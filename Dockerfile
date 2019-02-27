FROM gcr.io/positive-apex-225210/base-images/marketmanager:latest

# Copy source
COPY . /marketmanager/

WORKDIR /marketmanager
