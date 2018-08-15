FROM registry.gitlab.com/cryptohunters/accounts/python:3.6.6

COPY . /marketmanager/

RUN pip3 install -r /marketmanager/configs/requirements.txt
RUN pip3 install uwsgi

WORKDIR /marketmanager
