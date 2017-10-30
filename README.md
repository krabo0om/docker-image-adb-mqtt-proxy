# docker-image-adb-mqtt-proxy

Docker image which create a very basic proxy to remote control an android device with MQTT
Use this myself as a simple way to control my Nvidia shields, feel free to use, fork and/or submit improvements.



Environmental arguments:



MQTT_SERVER --> hostname/IP of MQTT broker

MQTT_PORT= --> port of the mqtt broker

MQTT_CLIENT --> clientname to use for mqtt communication (falls back to hostname if ommitted)

TOPIC --> base MQTT topic

USER --> mqtt username

PASSWORD --> mqtt password

ADB_DEVICE --> ip of the device to control (for multiple devices, seperate with commas)


```
The powerstate of each device will be pubished to:

<TOPIC>/<IP_OF_DEVICE>/stat
```


```
Commands for each device can be sent to:

<TOPIC>/<IP_OF_DEVICE>/cmd
```


For basic power commands, you can simply issue a ON/OFF command to the command topic.

e.g. adb/192.168.1.243/cmd --> ON


You can also send shell commands to the command topic

e.g. adb/192.168.1.243/cmd --> shell input keyevent KEYCODE_VOLUME_UP





