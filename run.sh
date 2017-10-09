#!/bin/bash
set -e

function ReportState () {
   echo "report power state"
   STATE=$(adb -s "$ADB_DEVICE:5555" shell dumpsys power | grep Display\ Power:\ state= || true)
   echo "state --> $STATE"
   if [ "$STATE" == "Display Power: state=ON" ]; then
   	 STATE="on"
   elif [ "$STATE" == "" ]; then
     ConnectADB
   else
  	 STATE="off"
   fi
   echo "Current power state of adb device: $STATE"
   mosquitto_pub -h "$MQTT_SERVER" -p "$MQTT_PORT" -u "$USER" -P "$PASSWORD" -t "$STAT_TOPIC" -q 1 -m "$STATE" -r || true
}

function ConnectADB () {
  echo "Connect to ADB device $ADB_DEVICE"
  adb connect "$ADB_DEVICE" || true
}

### MAIN CODE EXECUTION #####

# connect adb
ConnectADB

# report power state
sleep 2
ReportState

# read data
echo "Start listening for messages from MQTT-server $MQTT_SERVER"
while read -r message
do
  echo "Received message on MQTT: $message"
  
  if [ "$message" == "on" ]; then
  	echo "Turning on device..."
    adb -s "$ADB_DEVICE:5555" shell input keyevent KEYCODE_WAKEUP || true
  elif [ "$message" == "off" ]; then
  	echo "Turning off device..."
    adb -s "$ADB_DEVICE:5555" shell input keyevent KEYCODE_SLEEP || true
  elif [ "$message" == "state" ]; then
  	echo "Only report state..."
    ReportState
  else
  	echo "Run custom ADB shell command"
    adb -s "$ADB_DEVICE:5555" $message || true
  fi
  # report power state
  sleep .5
  ReportState

done < <(mosquitto_sub -h "$MQTT_SERVER" -p "$MQTT_PORT" -u "$USER" -P "$PASSWORD" -t "$TOPIC" -q 1 || true)

echo "exited..."