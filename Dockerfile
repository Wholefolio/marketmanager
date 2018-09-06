FROM gcr.io/production-185413/base-images/common:latest

# Copy source
COPY . /marketmanager/

WORKDIR /marketmanager
