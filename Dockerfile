FROM python:3.6.6-alpine

# Get necessary packages
RUN apk add postgresql-dev
RUN apk add git
RUN apk add openssh-client


# Get the private key to use in the pip3 install
ARG SSH_PRIVATE_KEY
RUN mkdir /root/.ssh/
RUN echo "${SSH_PRIVATE_KEY}" >> /root/.ssh/id_rsa && chmod 600 /root/.ssh/id_rsa
# make sure your domain is accepted
RUN >&2 ls -alh /root/.ssh/id_rsa && touch /root/.ssh/known_hosts
RUN ssh-keyscan gitlab.com >> /root/.ssh/known_hosts

# Copy source
COPY . /marketmanager/
# install requirements
RUN pip3 install -r /marketmanager/configs/requirements.txt
RUN pip3 install uwsgi

WORKDIR /marketmanager
