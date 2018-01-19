FROM python:3.6
LABEL maintainer="Marcel van der Veldt <m.vanderveldt@outlook.com>"

ENV LANG C.UTF-8

ENV MQTT_SERVER localhost
ENV MQTT_PORT 1883
ENV TOPIC adb
ENV USER mqttuser
ENV PASSWORD mqttpass
ENV ADB_DEVICE 192.168.1.243

RUN ls -s /config /root/.android
RUN pip3 install --no-cache-dir adb

# adb settings must be persistant
VOLUME /config

# Copy data for add-on
COPY adb_monitor.py /
RUN chmod a+x /adb_monitor.py

CMD [ "/adb_monitor.py" ]
