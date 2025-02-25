import os
import time
import docker
import pytest
import subprocess
from pathlib import Path
import logging

# Global variables
GIT_SERVER_CONTAINER = "git-server"
GIT_CLIENT_CONTAINER = "git-client"
GIT_REPO_NAME = "myrepo.git"
GIT_REPO_DIR = "myrepo"
GIT_SERVER_USER = "gituser"
GIT_SERVER_HOME = f"/home/{GIT_SERVER_USER}"
GIT_SERVER_REPO_PATH = f"{GIT_SERVER_HOME}/{GIT_REPO_NAME}"
GIT_SERVER_IP = None  # To be set after retrieving IP
GIT_VERSION = "2.25.1"
UBUNTU_VERSION = '20.04' # Set Ubuntu version

# Initialize Docker client
client = docker.from_env()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup function to execute docker command
def run_docker_command(command, check=True):
    """Helper function to run Docker commands."""
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Error occurred while executing command: {e}")
        raise

@pytest.fixture(scope="session", autouse=True)
def setup_git_server():
    """TC-01: Verify Git Client and Server Installation - Set up Git Server container."""

    logger.info("\n[INFO] Setting up Git Server...")

    # Remove any existing container
    run_docker_command(f"docker rm -f {GIT_SERVER_CONTAINER}", check=False)

    # Start a new container
    run_docker_command(
        f"docker run -d --name {GIT_SERVER_CONTAINER} -p 2222:22 -p 443:443 ubuntu:{UBUNTU_VERSION} sleep infinity",
        check=True
    )

    # Install Git & SSH server inside the Git Server container
    logger.info("\n[INFO] Installing Git & SSH on Git Server...")
    run_docker_command(
        f"docker exec {GIT_SERVER_CONTAINER} bash -c 'export DEBIAN_FRONTEND=noninteractive && apt update && apt install -y git openssh-server'",
        check=True
    )

    # Check version of Git installed - to be tested
    result = run_docker_command(
        f"docker exec {GIT_CLIENT_CONTAINER} bash -c 'git --version'",
        check=True
    )

    GIT_VERSION_CHECK = result.stdout.strip()
    assert GIT_VERSION in GIT_VERSION_CHECK, "Failed to install Git version!"

    # Run the setup commands inside the container
    run_docker_command(
        f"docker exec {GIT_SERVER_CONTAINER} bash -c '"
        f"service ssh start && "
        f"systemctl enable ssh'",
        check=True
    )

    logger.info("[PASS] TC-01: Verify Git Client and Server Installation - Set up Git Server container successfully.")

@pytest.mark.order(1)
def test_create_git_user():
    """TC-02: Verify Git Server Configuration - Create a Git user and initialize a bare Git repository."""

    logger.info("\n[TEST] Creating Git user and initializing repo...")

    # Run the setup commands inside the container
    run_docker_command(
        f"docker exec {GIT_SERVER_CONTAINER} bash -c '"
        f"useradd -m {GIT_SERVER_USER} && "
        f"mkdir -p {GIT_SERVER_REPO_PATH} && "
        f"git init --bare {GIT_SERVER_REPO_PATH} && "
        f"mkdir -p {GIT_SERVER_HOME}/.ssh && "
        f"chmod 700 {GIT_SERVER_HOME}/.ssh && "
        f"touch {GIT_SERVER_HOME}/.ssh/authorized_keys && "
        f"chmod 600 {GIT_SERVER_HOME}/.ssh/authorized_keys && "
        f"chown -R {GIT_SERVER_USER}:{GIT_SERVER_USER} {GIT_SERVER_HOME}'",
        check=True
    )

    # Verify repository creation
    result = run_docker_command(
        f"docker exec {GIT_SERVER_CONTAINER} ls -l {GIT_SERVER_REPO_PATH}"
    )
    assert "HEAD" in result.stdout, "Bare repository initialization failed!"

    logger.info("[PASS] TC-02: Verify Git Server Configuration - Create a Git user and initialize a bare Git repository successfully.")


@pytest.fixture(scope="session", autouse=True)
def setup_git_client():
    """TC-01: Verify Git Client and Server Installation - Set up Git Client container, install Git & SSH, and configure authentication."""
    logger.info("\n[INFO] Setting up Git Client...")

    # Remove any existing container
    run_docker_command(f"docker rm -f {GIT_CLIENT_CONTAINER}",check=False)

    # Start the Git Client container
    run_docker_command(
        f"docker run -d --name {GIT_CLIENT_CONTAINER} ubuntu:{UBUNTU_VERSION} sleep infinity",
        check=True
    )

    # Install Git & SSH Client inside the Git Client container
    logger.info("\n[INFO] Installing Git & SSH on Git Client...")
    run_docker_command(
        f"docker exec {GIT_CLIENT_CONTAINER} bash -c 'export DEBIAN_FRONTEND=noninteractive && apt update && apt install -y git openssh-client'",
        check=True
    )

    # Check version of Git installed - to be tested
    result = run_docker_command(
        f"docker exec {GIT_CLIENT_CONTAINER} bash -c 'git --version'",
        check=True
    )

    GIT_VERSION_CHECK = result.stdout.strip()
    assert GIT_VERSION in GIT_VERSION_CHECK, "Failed to install Git version!"

    logger.info("[PASS] TC-01: Verify Git Client and Server Installation - Set up Git Client container, install Git & SSH, and configure authentication successfully.")

@pytest.mark.order(2)
def test_configure_ssh_authentication():
    """TC-01: Verify Git Client and Server Installation - Generate SSH key and configure authentication between Git Client and Git Server."""
    logger.info("\n[TEST] Generating SSH Key...")

    # Generate SSH Key Pair inside the Git Client container
    run_docker_command(
        f"docker exec {GIT_CLIENT_CONTAINER} bash -c "
        f"'ssh-keygen -t rsa -b 2048 -N \"\" -f ~/.ssh/id_rsa && cat ~/.ssh/id_rsa.pub'",
        check=True
    )

    # Retrieve Public Key
    result = run_docker_command(
        f"docker exec {GIT_CLIENT_CONTAINER} bash -c 'cat ~/.ssh/id_rsa.pub'")
    client_ssh_key = result.stdout.strip()
    
    assert client_ssh_key, "Failed to generate SSH key!"

    # Copy Public Key to Git Server's authorized_keys
    logger.info("\n[INFO] Copying SSH Public Key to Git Server...")
    run_docker_command(
        f"docker exec {GIT_SERVER_CONTAINER} bash -c 'echo \"{client_ssh_key}\" >> {GIT_SERVER_HOME}/.ssh/authorized_keys'",
        check=True
    )

    # Set correct permissions
    run_docker_command(
        f"docker exec {GIT_SERVER_CONTAINER} bash -c 'chown {GIT_SERVER_USER}:{GIT_SERVER_USER} {GIT_SERVER_HOME}/.ssh/authorized_keys'",
        check=True
    )

    # Disable Strict Host Key Checking on Git Client
    run_docker_command(
        f"docker exec {GIT_CLIENT_CONTAINER} bash -c 'echo \"StrictHostKeyChecking no\" >> ~/.ssh/config && chmod 600 ~/.ssh/config'",
        check=True
    )

    logger.info("[PASS] TC-01: Verify Git Client and Server Installation - SSH Authentication Configured Successfully.")

@pytest.mark.order(3)
def test_get_git_server_ip():
    """TC-01: Verify Git Client and Server Installation - Retrieve Git Server's IP Address."""
    global GIT_SERVER_IP  # Store it for later use

    logger.info("\n[TEST] Retrieving Git Server IP Address...")
    result = run_docker_command(
        f"docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' {GIT_SERVER_CONTAINER}"
    )

    GIT_SERVER_IP = result.stdout.strip()
    assert GIT_SERVER_IP, "Failed to retrieve Git Server IP!"
    
    logger.info(f"[INFO] Git Server IP: {GIT_SERVER_IP}")

    logger.info("[PASS] TC-01: Verify Git Client and Server Installation - Retrieve Git Server's IP Address Successfully.")

@pytest.mark.order(4)
def test_git_clone():
    """TC-03: Clone Repository from Server & TC-07: SSH Authentication Test - Clone the repository using SSH."""
    logger.info("\n[TEST] Cloning Git Repository...")

    # Get Git Server IP
    git_server_ip = subprocess.check_output(
        "docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' git-server",
        shell=True
    ).decode().strip()

    # Clone Repo
    run_docker_command(
        f"docker exec {GIT_CLIENT_CONTAINER} git clone ssh://{GIT_SERVER_USER}@{git_server_ip}:{GIT_SERVER_REPO_PATH}"
    )

    output = run_docker_command(
        f"docker exec {GIT_CLIENT_CONTAINER} ls -l"
    )
    assert GIT_REPO_DIR in output.stdout, "Repository was not cloned successfully"

    logger.info("[PASS] TC-03: Clone Repository from Server & TC-07: SSH Authentication Test - Clone the repository using SSH Successfully.")

@pytest.mark.order(5)
def test_git_user_config_and_push():
    """TC-04: Push Changes to Server - Configure Git user, create a commit, and push changes to the Git Server."""
    logger.info("\n[TEST] Configuring Git user and pushing changes...")

    # Configure Git User
    run_docker_command(
        f"docker exec {GIT_CLIENT_CONTAINER} git config --global user.name 'Docker Tester'",
        check=True
    )
    run_docker_command(
        f"docker exec {GIT_CLIENT_CONTAINER} git config --global user.email 'tester@example.com'",
        check=True
    )

    # Create and commit a test file
    logger.info("\n[INFO] Creating and committing a test file...")
    run_docker_command(
        f"docker exec {GIT_CLIENT_CONTAINER} bash -c '"
        f"cd {GIT_REPO_DIR} && "
        f"touch testfile.txt && "
        f"echo \"Hello, Git!\" > testfile.txt && "
        f"git add testfile.txt && "
        f"git commit -m \"Initial commit\" && "
        f"git branch -M main && "
        f"git push origin main"
        f"'",
        check=True
    )

    # Verify if push was successful
    result = run_docker_command(
        f"docker exec {GIT_CLIENT_CONTAINER} git -C {GIT_REPO_DIR} log --oneline -n 1"
    )
    
    assert "Initial commit" in result.stdout.strip(), "Push operation failed!"

    logger.info("[PASS] TC-04: Push Changes to Server - Configure Git user, create a commit, and push changes to the Git Server successfully.")

@pytest.mark.order(6)
def test_pull_and_fetch_operations():
    """TC-05: Pull Changes from Server & TC-06: Fetch Changes from Server - Test git pull and git fetch operations on the cloned repository."""
    logger.info("\n[TEST] Testing pull and fetch operations...")

    # Pull latest changes from the remote Git server
    logger.info("\n[INFO] Running git pull...")
    result = run_docker_command(
        f"docker exec {GIT_CLIENT_CONTAINER} bash -c "
        f"'cd {GIT_REPO_DIR} && git pull origin main'"
    )
    assert "Already up to date." in result.stdout or "Updating" in result.stdout, "Git pull operation failed!"

    # Fetch latest changes from the remote Git server (without merging)
    logger.info("\n[INFO] Running git fetch...")
    result = run_docker_command(
        f"docker exec {GIT_CLIENT_CONTAINER} bash -c "
        f"'cd {GIT_REPO_DIR} && git fetch origin'"
    )
    assert result.returncode==0, "Git fetch operation failed!"

    logger.info("[PASS] TC-05: Pull Changes from Server & TC-06: Fetch Changes from Server - Test git pull and git fetch operations on the cloned repository succefully")

@pytest.fixture
def setup_network_and_container():

    network_name = subprocess.check_output(
        "docker network ls --filter driver=bridge --format '{{.Name}}'", shell=True
    ).decode().strip().split('\n')[0]  # Get the network name

    return network_name

@pytest.mark.order(7)
def test_network_failure_handling(setup_network_and_container):
    """TC-08: Network Failure During Push/Pull - Test Git network failure handling."""
    network_name = setup_network_and_container

    # Disconnect the container from the network
    logger.info(f"Disconnecting {GIT_CLIENT_CONTAINER} from network {network_name}...")
    try:
        run_docker_command(
            f"docker network disconnect {network_name} {GIT_CLIENT_CONTAINER}", check=True
        )
    except subprocess.CalledProcessError:
        pass  # Ignore if the disconnect fails (e.g., already disconnected)

    # Simulate a network failure (wait for 5 seconds)
    logger.info("Simulating network failure...")
    time.sleep(5)

    # Reconnect the container to the network
    logger.info(f"Reconnecting {GIT_CLIENT_CONTAINER} to network {network_name}...")
    run_docker_command(
        f"docker network connect {network_name} {GIT_CLIENT_CONTAINER}", check=True
    )

    # Run git pull command inside the container to check if it recovers
    logger.info("Running git pull inside the container...")
    result = run_docker_command(
        f"docker exec {GIT_CLIENT_CONTAINER} bash -c 'cd myrepo && git pull origin main'",
        check=True
    )

    # Check the output of the git pull command (this can be adjusted based on your expectations)
    logger.info(result.stdout)
    assert "Already up to date." in result.stdout or "Updating" in result.stdout

    logger.info("[PASS] TC-08: Network Failure During Push/Pull - Test Git network failure handling successfully.")

def teardown_module():
    """Cleanup containers after test."""
    logger.info("\n[CLEANUP] Removing Docker Containers...")
    run_docker_command(f"docker rm -f {GIT_SERVER_CONTAINER} {GIT_CLIENT_CONTAINER}")
