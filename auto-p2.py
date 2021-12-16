#################
# Script de automatización de un escenario de pruebas de un balanceador de tráfico
# Grupo 26 
# Autores: Gabriel Funes, Javier García y Pablo Real
#################
import sys
import subprocess
import os

inst = str(sys.argv[1]) # parámetro de la orden
dir = os.getcwd() # variable que guarda el directorio actual

try:
    num = int(sys.argv[2]) # parámetro de nº servidores (solo para orden "prepare")
except:
    num = 3

try:
    maq = str(sys.argv[2]) # parámetro de nombre de la mv a arrancar (solo para órdenes "launch" y "stop")
except:
    maq = NotImplemented

#################
# Comando PREPARE (crea los ficheros de diferencias y los de especificación, así como los bridges virtuales)
#################

if inst == "prepare":

    if (num > 0 and num < 6):

        # tenemos que estar dentro del directorio /mnt/tmp/carpeta_creada_por_nosotros

        f = open("auto-p2.json", "w")
        f.write("{\n\t\"num_serv\": " + str(num) + "\n}") 
        f.close()

        # creamos un directorio dinámico donde configurar los archivos de las MVs
        subprocess.call(["mkdir", "din"])

        # creacción bridges
        subprocess.call(["sudo", "brctl", "addbr", "LAN1"])
        subprocess.call(["sudo", "brctl", "addbr", "LAN2"])
        subprocess.call(["sudo", "ifconfig", "LAN1", "up"])
        subprocess.call(["sudo", "ifconfig", "LAN2", "up"])

        # configuración de la ip por defecto del host para conectarse al escenario
        subprocess.call(["sudo ifconfig LAN1 10.0.1.3/24"], shell=True)
        subprocess.call(["sudo ip route add 10.0.0.0/16 via 10.0.1.1"], shell=True)

        for i in range(1, num + 1): 

            # creacción imagenes .qcow2
            subprocess.call(["qemu-img", "create", "-f", "qcow2", "-b", "cdps-vm-base-pc1.qcow2", "s" + str(i) + ".qcow2"]) 
            
            # creacción plantillas
            fin = open ("plantilla-vm-pc1.xml", "r")
            fout = open("s" + str(i) + ".xml", "w")   

            for line in fin:
                if "<name>" in line:
                    fout.write("<name>s" + str(i) + "</name>\n")
                elif "<source file" in line:
                    fout.write("      <source file='" + dir + "/s" + str(i) + ".qcow2'/>\n") # usamos una variable que recoja el directorio donde ejecutamos python
                elif "<source bridge" in line:
                    fout.write("      <source bridge='LAN2'/>\n")
                else:
                    fout.write(line)  
            fin.close()
            fout.close()

            # creamos los directorios temporales para cada servidor s
            subprocess.call(["mkdir", "din/s" + str(i)])
            subprocess.call(["mkdir", "din/s" + str(i) + "/mv"])

            # copiamos al nuevo directorio los archivos a modificar

            subprocess.call(["sudo virt-copy-out -a " + dir + "/s" + str(i) + ".qcow2 /etc/hosts " + dir + "/din/s" + str(i) + "/mv"], shell=True)
            subprocess.call(["sudo virt-copy-out -a " + dir + "/s" + str(i) + ".qcow2 /etc/network/interfaces " + dir + "/din/s" + str(i) + "/mv"], shell=True)

            # archivos hostname
            subprocess.call(["echo s" + str(i) + " > " + dir + "/din/s" + str(i) + "/hostname"], shell=True)

            # archivos hosts
            fin = open (dir + "/din/s" + str(i) + "/mv/hosts", "r")
            fout = open (dir + "/din/s" + str(i) + "/hosts", "w")
            for line in fin:
                if "127.0.1.1" in line:
                    fout.write("127.0.1.1 s" + str(i) + "\n")
                else:
                    fout.write(line)
            fin.close()
            fout.close()

            # archivos interfaces
            fin = open (dir + "/din/s" + str(i) + "/mv/interfaces", "r")
            fout = open (dir + "/din/s" + str(i) + "/interfaces", "w")
            for line in fin:
                if "iface eth0 inet dhcp" in line:
                    fout.write("iface eth0 inet static\n    address 10.0.2.1" + str(i) + "\n    netmask 255.255.255.0\n    gateway 10.0.2.1\n    dns-nameservers 10.0.2.1")
                else:
                    fout.write(line)
            fin.close()
            fout.close()

            # copiamos los archivos en la máquina virtual
            subprocess.call(["sudo virt-copy-in -a " + dir + "/s" + str(i) + ".qcow2 " + dir + "/din/s" + str(i) + "/hosts /etc"], shell=True)
            subprocess.call(["sudo virt-copy-in -a " + dir + "/s" + str(i) + ".qcow2 " + dir + "/din/s" + str(i) + "/hostname /etc"], shell=True)
            subprocess.call(["sudo virt-copy-in -a " + dir + "/s" + str(i) + ".qcow2 " + dir + "/din/s" + str(i) + "/interfaces /etc/network"], shell=True)

        # LB #
        # creacción de la  MV
        subprocess.call(["qemu-img", "create", "-f", "qcow2", "-b", "cdps-vm-base-pc1.qcow2", "lb.qcow2"]) 
        # creacción plantilla
        fin = open ("plantilla-vm-pc1.xml", "r")
        fout = open("lb.xml", "w")   

        for line in fin:
            if "<name>" in line:
                fout.write("<name>lb</name>\n")
            elif "<source file" in line:
                fout.write("      <source file='" + dir + "/lb.qcow2'/>\n") # usamos una variable que recoja el directorio donde ejecutamos python
            elif "<source bridge" in line:
                fout.write("      <source bridge='LAN1'/>\n") 
            elif "</interface" in line: # hay que duplicar la sección interface al estar lb conectado a LAN1 y LAN2
                fout.write("    </interface>\n    <interface type='bridge'>\n      <source bridge='LAN2'/>\n      <model type='virtio'/>\n    </interface>\n")
            else:
                fout.write(line)  
        fin.close()
        fout.close()

        # creamos directorio temporal para lb

        subprocess.call(["mkdir", "din/lb"])
        subprocess.call(["mkdir", "din/lb/mv"])

        # copiamos al nuevo directorio los archivos a modificar

        subprocess.call(["sudo virt-copy-out -a " + dir + "/lb.qcow2 /etc/hosts " + dir + "/din/lb/mv"], shell=True)
        subprocess.call(["sudo virt-copy-out -a " + dir + "/lb.qcow2 /etc/network/interfaces " + dir + "/din/lb/mv"], shell=True)
        subprocess.call(["sudo virt-copy-out -a " + dir + "/lb.qcow2 /etc/haproxy/haproxy.cfg " + dir + "/din/lb/mv"], shell=True)

        # archivos hostname
        subprocess.call(["echo lb > " + dir + "/din/lb/hostname"], shell=True)

        # archivos hosts
        fin = open (dir + "/din/lb/mv/hosts", "r")
        fout = open (dir + "/din/lb/hosts", "w")
        for line in fin:
            if "127.0.1.1" in line:
                fout.write("127.0.1.1 lb\n")
            else:
                fout.write(line)
        fin.close()
        fout.close()

        # archivo interfaces
        fin = open (dir + "/din/lb/mv/interfaces", "r")
        fout = open (dir + "/din/lb/interfaces", "w")
        for line in fin:
            if "iface eth0 inet dhcp" in line:
                fout.write("iface eth0 inet static\n    address 10.0.1.1\n    netmask 255.255.255.0\n\nauto eth1\niface eth1 inet static\n    address 10.0.2.1\n    netmask 255.255.255.0")
            else:
                fout.write(line)
        fin.close()
        fout.close()

        # balanceador de tráfico
        fin = open (dir + "/din/lb/mv/haproxy.cfg", "r")
        fout = open (dir + "/din/lb/haproxy.cfg", "w")
        for line in fin:
            if "errorfile 504 /etc/haproxy/errors/504.http" in line:
                fout.write("\terrorfile 504 /etc/haproxy/errors/504.http\n\nfrontend lb\n\tbind *:80\n\tmode http\n\tdefault_backend webservers\n\nbackend webservers\n\tmode http\n\tbalance roundrobin\n")
                for i in range (1, num + 1):
                    fout.write("\tserver s" + str(i) + " 10.0.2.1" + str(i) + ":80 check\n")
            else:
                fout.write(line)
        fin.close()
        fout.close()

        # habilita el ip_forwarding para que el balanceador de tráfico funcione como router al arrancar
        subprocess.call(["sudo virt-edit -a lb.qcow2 /etc/sysctl.conf \-e 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/'"], shell=True)

        # editamos rc.local para parar el servidor apache2
        f = open (dir + "/din/lb/rc.local", "w")
        f.write("service apache2 stop \nexit 0")
        f.close()
        
        # copiamos los archivos en la máquina virtual
        subprocess.call(["sudo virt-copy-in -a " + dir + "/lb.qcow2 " + dir + "/din/lb/hosts /etc"], shell=True)
        subprocess.call(["sudo virt-copy-in -a " + dir + "/lb.qcow2 " + dir + "/din/lb/hostname /etc"], shell=True)
        subprocess.call(["sudo virt-copy-in -a " + dir + "/lb.qcow2 " + dir + "/din/lb/interfaces /etc/network"], shell=True)
        subprocess.call(["sudo virt-copy-in -a " + dir + "/lb.qcow2 " + dir + "/din/lb/haproxy.cfg /etc/haproxy"], shell=True)
        subprocess.call(["sudo virt-copy-in -a " + dir + "/lb.qcow2 " + dir + "/din/lb/rc.local /etc"], shell=True)

        # C1 #
        # creacción MV
        subprocess.call(["qemu-img", "create", "-f", "qcow2", "-b", "cdps-vm-base-pc1.qcow2", "c1.qcow2"])

        # creacción plantilla
        fin = open ("plantilla-vm-pc1.xml", "r")
        fout = open("c1.xml", "w")   

        for line in fin:
            if "<name>" in line:
                fout.write("<name>c1</name>\n")
            elif "<source file" in line:
                fout.write("      <source file='" + dir + "/c1.qcow2'/>\n") # usamos una variable que recoja el directorio donde ejecutamos python
            elif "<source bridge" in line:
                fout.write("      <source bridge='LAN1'/>\n")  
            else:
                fout.write(line)  
        fin.close()
        fout.close()

        # creamos directorio temporal para c1

        subprocess.call(["mkdir", "din/c1"])
        subprocess.call(["mkdir", "din/c1/mv"])

        # copiamos al nuevo directorio los archivos a modificar

        subprocess.call(["sudo virt-copy-out -a " + dir + "/c1.qcow2 /etc/hosts " + dir + "/din/c1/mv"], shell=True)
        subprocess.call(["sudo virt-copy-out -a " + dir + "/c1.qcow2 /etc/network/interfaces " + dir + "/din/c1/mv"], shell=True)

        # archivos hostname
        subprocess.call(["echo c1 > " + dir + "/din/c1/hostname"], shell=True)

        # archivos hosts
        fin = open (dir + "/din/c1/mv/hosts", "r")
        fout = open (dir + "/din/c1/hosts", "w")
        for line in fin:
            if "127.0.1.1" in line:
                fout.write("127.0.1.1 c1\n")
            else:
                fout.write(line)
        fin.close()
        fout.close()

        # archivo interfaces
        fin = open (dir + "/din/c1/mv/interfaces", "r")
        fout = open (dir + "/din/c1/interfaces", "w")
        for line in fin:
            if "iface eth0 inet dhcp" in line:
                fout.write("iface eth0 inet static\n    address 10.0.1.2\n    netmask 255.255.255.0\n    gateway 10.0.1.1\n    dns-nameservers 10.0.1.1")
            else:
                fout.write(line)
        fin.close()
        fout.close()

        # copiamos los archivos en la máquina virtual
        subprocess.call(["sudo virt-copy-in -a " + dir + "/c1.qcow2 " + dir + "/din/c1/hosts /etc"], shell=True)
        subprocess.call(["sudo virt-copy-in -a " + dir + "/c1.qcow2 " + dir + "/din/c1/hostname /etc"], shell=True)
        subprocess.call(["sudo virt-copy-in -a " + dir + "/c1.qcow2 " + dir + "/din/c1/interfaces /etc/network"], shell=True)

        # eliminamos directorio dinámico para que el proceso sea transparente para el usuario
        subprocess.call(["rm -rf din"], shell = True)

    else:    
        print("Solo se pueden configurar de 1 a 5 servidores") 

#################
# Comando LAUNCH (arranca las MVs y muestra su consola)
#################

elif inst == "launch":

    f = open ("auto-p2.json", "r")
    for line in f:
        if "\"num_serv" in line:
            numcre = int(''.join(filter(str.isdigit, line)))
    f.close()

    # miramos si se introduce el nombre de una MV para arrancarla individualmente
    if len(sys.argv) == 3:

        for i in range(1, numcre + 1):
            
            # arrancado de MVs y muetra de consola en caso de arrancar algún servidor
            if maq == "s" + str(i):
                subprocess.call(["sudo", "virsh", "define", "" + maq + ".xml"])    
                subprocess.call(["sudo", "virsh", "start", "" + maq])
                subprocess.call(["xterm -rv -sb -rightbar -fa  monospace -fs  10 -title  '" + maq + "\' -e  'sudo virsh console " + maq + "\'&"], shell = True)
                sys.exit()

        # arrancado de MV y muetra de consola en caso de arrancar lb
        if maq == "lb":
            subprocess.call(["sudo", "virsh", "define", "lb.xml"])
            subprocess.call(["sudo", "virsh", "start", "lb"])
            subprocess.call(["xterm -rv -sb -rightbar -fa  monospace -fs  10 -title  'lb\' -e  'sudo virsh console lb\'&"], shell = True)

        # arrancado de MV y muetra de consola en caso de arrancar c1
        elif maq == "c1":
            subprocess.call(["sudo", "virsh", "define", "c1.xml"])
            subprocess.call(["sudo", "virsh", "start", "c1"])
            subprocess.call(["xterm -rv -sb -rightbar -fa  monospace -fs  10 -title  'c1\' -e  'sudo virsh console c1\'&"], shell = True)
            
        else:
            print("Error, el nombre de la máquina virtual a arrancar que ha introduido no es válido")
    
    else:
     
        for i in range(1, numcre + 1):

            # arrancado de MVs
            subprocess.call(["sudo", "virsh", "define", "s" + str(i) + ".xml"])    
            subprocess.call(["sudo", "virsh", "start", "s" + str(i)])

            # mostrar consola de los servidores
            subprocess.call(["xterm -rv -sb -rightbar -fa  monospace -fs  10 -title  's" + str(i) + "\' -e  'sudo virsh console s" + str(i) + "\'&"], shell = True) 

        # arrancado de MVs
        subprocess.call(["sudo", "virsh", "define", "lb.xml"])
        subprocess.call(["sudo", "virsh", "start", "lb"])
        subprocess.call(["sudo", "virsh", "define", "c1.xml"])
        subprocess.call(["sudo", "virsh", "start", "c1"])

        # mostrar consola
        subprocess.call(["xterm -rv -sb -rightbar -fa  monospace -fs  10 -title  'lb\' -e  'sudo virsh console lb\'&"], shell = True)
        subprocess.call(["xterm -rv -sb -rightbar -fa  monospace -fs  10 -title  'c1\' -e  'sudo virsh console c1\'&"], shell = True)

#################
# Comando MONITOR (presenta el estado de todas las MVs)
#################

elif inst == "monitor":

    # abrir una consola para el comando virsh list que se actualiza cada 0.1s con el comando watch MIRAR COMO CERRARLA
    subprocess.call(["xterm -rv -sb -rightbar -fa  monospace -fs 10 -title  'Monitor\' -e 'watch -n 0.1 sudo virsh list --all \' &"], shell=True)

#################
# Comando STOP (para las MVs sin liberarlas)
#################

elif inst == "stop":

    f = open ("auto-p2.json", "r")
    for line in f:
        if "\"num_serv" in line:
            numcre = int(''.join(filter(str.isdigit, line)))
    f.close()

    # miramos si se introduce el nombre de una MV para pararla individualmente
    if len(sys.argv) == 3:

        for i in range(1, numcre + 1):
            
            # parada de MVs en caso de parar algún servidor
            if maq == "s" + str(i):
                subprocess.call(["sudo", "virsh", "shutdown", "" + maq])
                sys.exit()

        # parada de MV en caso de arrancar lb
        if maq == "lb":
            subprocess.call(["sudo", "virsh", "shutdown", "lb"])

        # parada de MV en caso de arrancar c1
        elif maq == "c1":
            subprocess.call(["sudo", "virsh", "shutdown", "c1"])
            
        else:
            print("Error, el nombre de la máquina virtual a arrancar que ha introduido no es válido")

    else:
     
        for i in range(1, numcre + 1):

            # parada de MVs servidores
            subprocess.call(["sudo", "virsh", "shutdown", "s" + str(i)]) 

        # parada de MVs
        subprocess.call(["sudo", "virsh", "shutdown", "lb"]) 
        subprocess.call(["sudo", "virsh", "shutdown", "c1"]) 

#################
# Comando RELEASE (libera el escenario)
#################

elif inst == "release":

    f = open ("auto-p2.json", "r")
    for line in f:
        if "\"num_serv" in line:
            numcre = int(''.join(filter(str.isdigit, line)))
    f.close()

    for i in range(1, numcre + 1):

        # servidores
        subprocess.call(["sudo", "virsh", "destroy", "s" + str(i)])
        subprocess.call(["sudo", "virsh", "undefine", "s" + str(i)])

    # lb y c1
    subprocess.call(["sudo", "virsh", "destroy", "lb"]) 
    subprocess.call(["sudo", "virsh", "undefine", "lb"]) 
    subprocess.call(["sudo", "virsh", "destroy", "c1"])
    subprocess.call(["sudo", "virsh", "undefine", "c1"]) 

    # bridges
    subprocess.call(["sudo", "ifconfig", "LAN1", "down"]) 
    subprocess.call(["sudo", "ifconfig", "LAN2", "down"])
    subprocess.call(["sudo", "brctl", "delbr", "LAN1"])
    subprocess.call(["sudo", "brctl", "delbr", "LAN2"])

    # borrado de archivos del directorio
    subprocess.call(["rm -f auto-p2.json"], shell = True)

    for i in range(1, numcre + 1):
        subprocess.call(["rm -f s" + str(i) + ".qcow2"], shell = True)
        subprocess.call(["rm -f s" + str(i) + ".xml"], shell = True)

    subprocess.call(["rm -f lb.qcow2"], shell = True)
    subprocess.call(["rm -f lb.xml"], shell = True)
    subprocess.call(["rm -f c1.qcow2"], shell = True)
    subprocess.call(["rm -f c1.xml"], shell = True)
    
# Si no es ninguno de los comandos
else:
    print("Error: Solo se deben proveer los comandos prepare, launch, stop, release o monitor")
