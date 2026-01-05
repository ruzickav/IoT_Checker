ARG BUILD_FROM
FROM $BUILD_FROM

# Instalace Pythonu, Pipu a Pingu
RUN apk add --no-cache \
    python3 \
    py3-pip \
    iputils

# Instalace MQTT knihovny
RUN pip3 install paho-mqtt --break-system-packages

# Kopírování souborů
COPY run.py /
COPY run.sh /
RUN chmod a+x /run.sh /run.py

CMD [ "/run.sh" ]