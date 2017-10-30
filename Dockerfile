FROM debian:jessie
MAINTAINER Marcel van der Veldt <m.vanderveldt@outlook.com>

ENV LANG C.UTF-8

RUN apt-get update
RUN apt-get install -y android-tools-adb mosquitto-clients jq python python-pip
RUN pip install paho-mqtt


# Copy data for add-on
COPY adb_monitor.py /
RUN chmod a+x /adb_monitor.py

CMD [ "/adb_monitor.py" ]