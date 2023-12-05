FROM nvidia/cuda:11.7.1-runtime-ubuntu22.04

RUN apt-get update -y && apt-get install -y gcc python3.11-dev python3.11-distutils curl
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
RUN python3.11 get-pip.py

WORKDIR /fschat
COPY . /fschat
RUN pip3 install --upgrade pip  # enable PEP 660 support
RUN --mount=type=cache,target=/root/.cache pip3 install -e /fschat --default-timeout=1000
