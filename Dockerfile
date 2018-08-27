FROM python:3.6.6-alpine

COPY . /marketmanager/

RUN apk add postgresql-dev
RUN apk add git
RUN apk add openssh-client

RUN pip3 install -r /marketmanager/configs/requirements.txt
RUN pip3 install uwsgi

WORKDIR /marketmanager
