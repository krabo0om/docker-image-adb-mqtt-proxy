# docker-image-adb-mqtt-proxy

Docker image which create a very basic proxy to remote control an android device with MQTT
Use this myself as a simple way to control my Nvidia shields, feel free to use, fork and/or submit improvements.

Environmental arguments:

MQTT_SERVER --> hostname/IP of MQTT broker
MQTT_PORT= --> port of the mqtt broker
TOPIC --> topic to listen for commands
STAT_TOPIC --> topic where powerstate of device is sent
USER --> mqtt username
PASSWORD --> mqtt password
ADB_DEVICE --> ip of the device to control

