# Automatizaci-n-en-python

Este script en python se ha desarrollado para el despliegue de un escenario de pruebas de un balanceador de tráfico (LB). 
Instrucciones:
• prepare, para crear los ficheros .qcow2 de diferencias y los de especificación en XML
de cada MV, así como los bridges virtuales que soportan las LAN del escenario.
• launch, para arrancar las máquinas virtuales y mostrar su consola.
• stop, para parar las máquinas virtuales (sin liberarlas).
• release, para liberar el escenario, borrando todos los ficheros creados.
• monitor, para monitorizar los cambios que se realicen en las MVs

El número de servidores web a arrancar es configurable (de 1 a 5) y se especifica en el segundo parámetro de línea de comandos. Por defecto, este es 3. El valor del número de servidores sólo se especifica con el comando “prepare”. Ese número se almacena en un fichero de configuración en el directorio de trabajo (autop2.json) y el resto de los comandos (launch, stop, release) lo leerán de ese fichero. El formato con el que se almacena es JSON.

Este script es NO INTERACTIVO con el usuario.

Además, se realiza la configuración y arranque automático del balanceador de tráfico HAproxy, de manera que cuando se arranque la MV esté disponible automáticamente el servicio
de balanceo de tráfico entre servidores web.
