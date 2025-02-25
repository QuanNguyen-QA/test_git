#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status
set -o pipefail  # Ensure pipeline errors are caught

LOG_FILE="git_test.log"
exec > >(tee -a "$LOG_FILE") 2>&1  # Log all output to a file

# Variables
GIT_SERVER_CONTAINER="git-server"
GIT_CLIENT_CONTAINER="git-client"
GIT_REPO_NAME="myrepo.git"
GIT_SERVER_USER="gituser"
GIT_SERVER_HOME="/home/$GIT_SERVER_USER"
GIT_SERVER_REPO_PATH="$GIT_SERVER_HOME/$GIT_REPO_NAME"
UBUNTU_VERSION='20.04' # Set Ubuntu version

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

cleanup() {
    log "Cleaning up existing containers..."
    docker rm -f $GIT_SERVER_CONTAINER $GIT_CLIENT_CONTAINER || true
}
trap cleanup EXIT  # Ensure cleanup runs on exit

setup_git_server() {

    # TC-01: Verify Git Client and Server Installation
    log "Setting up Git Server Container..."
    docker pull ubuntu:latest
    docker run -d --name $GIT_SERVER_CONTAINER -p 2222:22 -p 443:443 ubuntu:$UBUNTU_VERSION bash -c "sleep infinity"
    
    docker exec $GIT_SERVER_CONTAINER apt update
    docker exec $GIT_SERVER_CONTAINER bash -c " export DEBIAN_FRONTEND=noninteractive && apt install -y git openssh-server nginx"

    docker exec $GIT_SERVER_CONTAINER bash -c "
        service ssh start &&
        systemctl enable ssh
    "
    # TC-02: Verify Git Server Configuration
    log "Setting up SSL for HTTPS..."
    docker exec $GIT_SERVER_CONTAINER bash -c "
        mkdir -p /etc/ssl/private /etc/ssl/certs &&
        openssl req -new -newkey rsa:2048 -days 365 -nodes -x509 \
        -keyout /etc/ssl/private/gitserver.key \
        -out /etc/ssl/certs/gitserver.crt \
        -subj '/C=US/ST=California/L=SanFrancisco/O=Git/OU=GitServer/CN=localhost'
    "

    log "Creating Git user and repository..."
    docker exec $GIT_SERVER_CONTAINER bash -c "
        useradd -m $GIT_SERVER_USER &&
        mkdir -p $GIT_SERVER_REPO_PATH &&
        git init --bare $GIT_SERVER_REPO_PATH &&
        mkdir -p $GIT_SERVER_HOME/.ssh &&
        chmod 700 $GIT_SERVER_HOME/.ssh &&
        touch $GIT_SERVER_HOME/.ssh/authorized_keys &&
        chmod 600 $GIT_SERVER_HOME/.ssh/authorized_keys &&
        chown -R $GIT_SERVER_USER:$GIT_SERVER_USER $GIT_SERVER_HOME
    "
}

setup_git_client() {
    # TC-01: Verify Git Client and Server Installation
    log "Setting up Git Client Container..."
    docker run -d --name $GIT_CLIENT_CONTAINER ubuntu:$UBUNTU_VERSION bash -c "sleep infinity"
    
    docker exec $GIT_CLIENT_CONTAINER apt update
    docker exec $GIT_CLIENT_CONTAINER bash -c "export DEBIAN_FRONTEND=noninteractive && apt install -y git openssh-client"
    
    log "Generating SSH key for authentication..."
    docker exec $GIT_CLIENT_CONTAINER bash -c "
        ssh-keygen -t rsa -b 2048 -N '' -f ~/.ssh/id_rsa &&
        cat ~/.ssh/id_rsa.pub
    " > id_rsa.pub

    log "Copying SSH key to Git Server..."
    docker exec -i $GIT_SERVER_CONTAINER bash -c "cat >> $GIT_SERVER_HOME/.ssh/authorized_keys" < id_rsa.pub
    docker exec $GIT_SERVER_CONTAINER bash -c "
        chown $GIT_SERVER_USER:$GIT_SERVER_USER $GIT_SERVER_HOME/.ssh/authorized_keys
    "
}

clone_and_test_repository() {
    # TC-03: Clone Repository from Server & TC-07: SSH Authentication Test
    log "Testing SSH connection..."
    docker exec $GIT_CLIENT_CONTAINER bash -c "
        echo 'StrictHostKeyChecking no' >> ~/.ssh/config &&
        chmod 600 ~/.ssh/config
    "

    GIT_SERVER_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $GIT_SERVER_CONTAINER)

    log "Cloning repository from Git Server..."
    docker exec $GIT_CLIENT_CONTAINER bash -c "
        GIT_SSH_COMMAND='ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no' git clone ssh://$GIT_SERVER_USER@$GIT_SERVER_IP:$GIT_SERVER_REPO_PATH
    "

    # TC-04: Push Changes to Server
    log "Configuring Git user and testing push..."
    docker exec $GIT_CLIENT_CONTAINER bash -c "
        git config --global user.name 'Docker Tester' &&
        git config --global user.email 'tester@example.com' &&
        cd myrepo &&
        touch testfile.txt &&
        echo 'Hello, Git!' > testfile.txt &&
        git add testfile.txt &&
        git commit -m 'Initial commit' &&
        git branch -M main &&
        git push origin main
    "

    # TC-05: Pull Changes from Server & TC-06: Fetch Changes from Server
    log "Testing pull and fetch operations..."
    docker exec $GIT_CLIENT_CONTAINER bash -c "
        cd myrepo &&
        git pull origin main &&
        git fetch origin
    "
}

simulate_network_failure() {
    # TC-08: Network Failure During Push/Pull
    log "Simulating network failure..."
    NETWORK_NAME=$(docker network ls --filter driver=bridge --format "{{.Name}}" | head -n 1)
    
    log "Disconnecting Git Client from network..."
    docker network disconnect $NETWORK_NAME $GIT_CLIENT_CONTAINER || true
    
    sleep 5
    
    log "Reconnecting Git Client to network..."
    docker network connect $NETWORK_NAME $GIT_CLIENT_CONTAINER

    docker exec $GIT_CLIENT_CONTAINER bash -c "
        cd myrepo &&
        git pull origin main
    "
}

main() {
    cleanup
    setup_git_server
    setup_git_client
    clone_and_test_repository
    simulate_network_failure
    log "All tests completed successfully!"
}

main
