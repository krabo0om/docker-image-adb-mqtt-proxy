#!/usr/bin/env python

import logging
import os
import signal
import socket
import sys
import time
import ssl
import paho.mqtt.client as mqtt
import socket
from traceback import format_exc
import subprocess

# Script name (without extension) used for config/logfile names
HOSTNAME = socket.gethostname()
APPNAME = os.path.splitext(os.path.basename(__file__))[0]

MQTT_HOST = os.environ['MQTT_SERVER']
MQTT_PORT = int(os.environ['MQTT_PORT'])
MQTT_USERNAME = os.environ['USER']
MQTT_PASSWORD = os.environ['PASSWORD']
MQTT_CLIENT_ID = os.environ['MQTT_CLIENT'] if 'MQTT_CLIENT' in os.environ else HOSTNAME
MQTT_TOPIC = os.environ['TOPIC']
ADB_DEVICES = os.environ['ADB_DEVICE'].split(",")

# other MQTT settings
MQTT_QOS = 2
MQTT_RETAIN = True
MQTT_CLEAN_SESSION = True
MQTT_LWT = "clients/%s" % MQTT_CLIENT_ID

# Initialise logger
LOGFORMAT = '%(asctime)-15s %(levelname)-5s %(message)s'
logger = logging.getLogger(APPNAME)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO) # loglevel for console
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

logger.info("Starting " + APPNAME)
for adb_device in ADB_DEVICES:
    logger.info("Monitoring ADB Device: %s" % adb_device)
    logger.info("    Publish ADB Stats to topic: %s/%s/stat" % (MQTT_TOPIC, adb_device))
    logger.info("    Monitor ADB commands on topic: %s/%s/cmd" % (MQTT_TOPIC, adb_device))

# Create the MQTT client
mqttc = mqtt.Client(MQTT_CLIENT_ID, clean_session=MQTT_CLEAN_SESSION)

# keep states in disconnect
STATES = {}

# MQTT callbacks
def on_connect(mosq, obj, flags, result_code):
    """
    Handle connections (or failures) to the broker.
    This is called after the client has received a CONNACK message
    from the broker in response to calling connect().
    The parameter rc is an integer giving the return code:

    0: Success
    1: Refused . unacceptable protocol version
    2: Refused . identifier rejected
    3: Refused . server unavailable
    4: Refused . bad user name or password (MQTT v3.1 broker only)
    5: Refused . not authorised (MQTT v3.1 broker only)
    """
    if result_code == 0:
        logger.info("Connected to %s:%s" % (MQTT_HOST, MQTT_PORT))

        # Subscribe incoming topic
        for adb_device in ADB_DEVICES:
            mqtt_topic = "%s/%s/cmd" %(MQTT_TOPIC, adb_device)
            logger.debug("subscribing to topic %s" % mqtt_topic)
            mqttc.subscribe(mqtt_topic, qos=MQTT_QOS)
        
        # Publish retained LWT as per http://stackoverflow.com/questions/19057835/how-to-find-connected-mqtt-client-details/19071979#19071979
        # See also the will_set function in connect() below
        mqttc.publish(MQTT_LWT, "1", qos=0, retain=True)

    elif result_code == 1:
        logger.info("Connection refused - unacceptable protocol version")
    elif result_code == 2:
        logger.info("Connection refused - identifier rejected")
    elif result_code == 3:
        logger.info("Connection refused - server unavailable")
    elif result_code == 4:
        logger.info("Connection refused - bad user name or password")
    elif result_code == 5:
        logger.info("Connection refused - not authorised")
    else:
        logger.warning("Connection failed - result code %d" % (result_code))

def on_disconnect(mosq, obj, result_code):
    """
    Handle disconnections from the broker
    """
    if result_code == 0:
        logger.info("Clean disconnection from broker")
    else:
        logger.info("Broker connection lost. Retrying in 5s...")
        time.sleep(5)

def on_message(mosq, obj, msg):
    """
    Handle incoming messages
    """
    logger.debug("Received MQTT message --> topic: %s - payload: %s" % (msg.topic, msg.payload))
    topicparts = msg.topic.split("/")
    adb_device = topicparts[-2]
    value = msg.payload.strip()
    logger.info("Incoming message for device %s -> %s" % (adb_device, value))

    if adb_device not in ADB_DEVICES:
        "Requested device is not monitored !"
    elif value in ["1", "on", "ON"]:
        adb_command(adb_device, "shell input keyevent KEYCODE_WAKEUP")
    elif value in ["0", "off", "OFF"]:
        adb_command(adb_device, "shell input keyevent KEYCODE_SLEEP")
    else:
        # custom adb command
        adb_command(adb_device, value)
    publish_state()
# End of MQTT callbacks

def adb_command(adb_device, adb_cmd):
    '''issue adb command'''
    output = ""
    if adb_cmd and adb_cmd.startswith("shell") and adb_cmd != "shell":
        # issue adb command
        adb_cmd = "adb -s %s:5555 %s" %(adb_device, adb_cmd)
        adb_proc = subprocess.Popen(adb_cmd, shell=True, stdout=subprocess.PIPE)
        output = adb_proc.communicate()[0]
        returncode = adb_proc.returncode
        if returncode > 0:
            logger.error("ADB command failed - issue reconnect...")
            adb_connect()
            adb_proc = subprocess.Popen(adb_cmd, shell=True, stdout=subprocess.PIPE)
            output = adb_proc.communicate()[0]
    else:
        logger.error("Invalid command, only shell commands are supported")
    return output

def adb_connect():
    '''conect adb devices'''
    logger.info("Connect to ADB service ")
    for adb_device in ADB_DEVICES:
        adb_device = adb_device + ":5555"
        subprocess.call('adb disconnect %s' % adb_device, shell=True)
        subprocess.call('adb connect %s' % adb_device, shell=True)


def publish_state():
    ''' publish state of adb devices'''
    for adb_device in ADB_DEVICES:
        state = adb_command(adb_device, "shell dumpsys power | grep Display\ Power:\ state=")
        if "Display Power: state=ON" in state:
            state = "ON"
        else:
            state = "OFF"
        if STATES.get(adb_device,"") != state:
            logger.info("State changed for device %s - new state: %s" %(adb_device, state))
            mqtt_topic = "%s/%s/stat" % (MQTT_TOPIC, adb_device)
            mqttc.publish(mqtt_topic, payload=state, qos=MQTT_QOS, retain=MQTT_RETAIN)
            STATES[adb_device] = state


def cleanup(signum, frame):
    """
    Signal handler to ensure we disconnect cleanly
    in the event of a SIGTERM or SIGINT.
    """

    # Publish our LWT and cleanup the MQTT connection
    logger.info("Disconnecting from broker...")
    mqttc.publish(MQTT_LWT, "0", qos=0, retain=True)
    mqttc.disconnect()
    mqttc.loop_stop()

    # Exit from our application
    logger.info("Exiting on signal %d" % (signum))
    sys.exit(signum)

def connect():
    """
    Connect to the broker, define the callbacks, and subscribe
    This will also set the Last Will and Testament (LWT)
    The LWT will be published in the event of an unclean or
    unexpected disconnection.
    """
    # Add the callbacks
    mqttc.on_connect = on_connect
    mqttc.on_disconnect = on_disconnect
    mqttc.on_message = on_message

    # Set the login details
    if MQTT_USERNAME:
        mqttc.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    # Set the Last Will and Testament (LWT) *before* connecting
    mqttc.will_set(MQTT_LWT, payload="0", qos=0, retain=True)

    # Attempt to connect
    logger.debug("Connecting to %s:%d..." % (MQTT_HOST, MQTT_PORT))
    try:
        mqttc.connect(MQTT_HOST, MQTT_PORT, 60)
    except Exception as e:
        logger.error("Error connecting to %s:%d: %s" % (MQTT_HOST, MQTT_PORT, str(e)))
        sys.exit(2)

    # Let the connection run forever
    mqttc.loop_start()


def poll():
    """
    The main loop in which we monitor the state of the devices
    and publish any changes.
    """
    check_interval = 1
    while True:
        try:
            # monitor states
            publish_state()
        except Exception as exc:
            logger.error(str(exc))
            logger.debug(format_exc(sys.exc_info()))
        time.sleep(check_interval)

# Use the signal module to handle signals
for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT]:
    signal.signal(sig, cleanup)

# Connect to broker and begin polling our GPIO pins
connect()
poll()
