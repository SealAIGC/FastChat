FROM nvidia/cuda:11.7.1-runtime-ubuntu20.04

RUN apt-get update -y && apt-get install -y python3.9 python3.9-distutils curl
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
RUN python3.9 get-pip.py

WORKDIR /fschat
COPY . /fschat
RUN pip3 install --upgrade pip  # enable PEP 660 support
RUN pip3 install -e /fschat