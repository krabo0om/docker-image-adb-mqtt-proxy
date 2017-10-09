FROM debian:jessie
MAINTAINER Marcel van der Veldt <m.vanderveldt@outlook.com>

ENV LANG C.UTF-8

RUN apt-get update
RUN apt-get install -y android-tools-adb
RUN apt-get install -y mosquitto-clients
RUN apt-get install -y jq


# Copy data for add-on
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]