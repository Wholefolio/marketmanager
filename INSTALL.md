# Local setup
1. Install python3 and pip(Ubuntu examples):
```
apt-get install python3
apt-get install python3-pip
```
2. Get docker: https://docs.docker.com/install/linux/docker-ce/ubuntu/#uninstall-old-versions
3. Clone the application locally:
`git clone https://gitlab.com/cryptohunters/marketmanager/`
4. Install pipenv and install the depedencies:
`pip3 install pipenv && pipenv install`
5. Set up the env variables - this assumes you have a running InfluxDB container and PostgreSQL database
`source .env`
6. Start up the virtual env
`pipenv shell`

# Compose
## Prerequisites
You must have Docker installed locally and docker-compose to bring up the containers
## Run
`cd examples/compose && docker-compose up -d`

# Kubernetes
To install the manifests you must have kubectl installed and prepared for your cluster
`kubectl config current-context`  
To install the manifests run:
`kubectl apply -f install/kubernetes/`