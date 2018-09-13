FROM gcr.io/production-185413/base-images/marketmanager:latest

# Copy source
COPY . /marketmanager/

WORKDIR /marketmanager
