FROM python:3.7.10-alpine


RUN apk add postgresql-dev git gcc linux-headers musl-dev zlib-dev jpeg-dev python3-dev g++ libffi-dev

# Copy source
COPY . /marketmanager/

WORKDIR /marketmanager

RUN pip3 install pipenv && pipenv install

RUN apk del gcc g++


CMD ["pipenv shell && uwsgi -c config/uwsgi.ini"]