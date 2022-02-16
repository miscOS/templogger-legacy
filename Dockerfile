FROM alpine:3.11

WORKDIR /usr/src/app

RUN apk add --no-cache python3 && \
    pip3 install --upgrade pip setuptools && \
    if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi && \
    if [ ! -e /usr/bin/python ]; then ln -sf /usr/bin/python3 /usr/bin/python; fi

RUN apk add --no-cache libusb && \
    pip install pyusb paho-mqtt

RUN mkdir /usr/src/app/logfile

COPY . /usr/src/app

ENTRYPOINT ["python" , "templogger.py"]