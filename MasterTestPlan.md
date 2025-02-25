# Master Test Plan: Git Client-Server Communication using Docker

## 1. Introduction
This document outlines the Master Test Plan for verifying the communication between a Git client and a Git server using two Docker hosts. One host will function as the Git client, while the other will serve as the Git server.

## 2. Test Objectives
- Verify the setup and configuration of Git client and server in Docker containers.
- Validate secure communication between the Git client and server.
- Ensure proper Git operations (clone, pull, push, fetch, etc.) are working.
- Test authentication and authorization mechanisms.
- Validate error handling and logging mechanisms.

## 3. Test Scope
- Functional Testing
- Security Testing
- Performance Testing
- Reliability Testing

Due to the time scope, we limited our test environment with Ubuntu docker on Github.

## 4. Test Environment
- Github Action
- Docker installed for both client and server machines
- Git installed on both Docker containers
- SSH or HTTPS-based authentication for secure communication
- Local and remote repositories for testing
- Specific version of toolchain under test:
- - ubuntu:20.04
- - docker:24.0.6
- - pytest:7.4.0
- - pytest-html:4.0.0

## 5. Test Cases in the Phase #1

| **Test Case ID** | **Description** | **Preconditions** | **Steps** | **Expected Result** |
|-----------------|---------------|----------------|---------|----------------|
| **TC-01** | Verify Git Client and Server Installation | Docker must be installed on both hosts | 1. Start a Git server container with a Git repository.<br>2. Start a Git client container and install Git.<br>3. Verify Git installation with `git --version`. | Git is successfully installed and accessible on both containers. |
| **TC-02** | Verify Git Server Configuration | Git server container must be running | 1. Access the Git server container.<br>2. Initialize a bare Git repository (`git init --bare myrepo.git`).<br>3. Check the repository structure. | The Git repository is initialized correctly and ready for use. |
| **TC-03** | Clone Repository from Server | Git server must have a repository | 1. From the Git client, run `git clone user@server:/path/to/repo.git`.<br>2. Check if the repository is cloned successfully. | Repository is cloned without errors. |
| **TC-04** | Push Changes to Server | Git client must have write access | 1. Modify a file and commit the changes.<br>2. Run `git push origin main`.<br>3. Verify the changes on the server. | Changes are successfully pushed to the server. |
| **TC-05** | Pull Changes from Server | Remote repository has new commits | 1. From the client, run `git pull origin main`.<br>2. Verify if the latest changes are fetched and merged. | Changes are successfully pulled from the server. |
| **TC-06** | Fetch Changes from Server | Updates are available on the remote repository | 1. Run `git fetch origin` on the client.<br>2. Verify that the remote changes are reflected locally. | Fetch operation is successful, and changes are listed. |
| **TC-07** | SSH Authentication Test | SSH keys are set up between client and server | 1. Attempt to clone using `git clone ssh://user@server:/repo.git`.<br>2. Verify that the operation is successful. | Clone operation should work without password prompt if SSH keys are configured correctly. |
| **TC-08** | Network Failure During Push/Pull | Active Git session | 1. Disconnect network while executing `git push` or `git pull`.<br>2. Reconnect and retry the operation. | Operation should resume or provide an appropriate error message. |

## 6. Test Cases in the Phase #2
| **Test Case ID** | **Description** | **Preconditions** | **Steps** | **Expected Result** |
|-----------------|---------------|----------------|---------|----------------|
| **TC-09** | HTTPS Authentication Test | Git server must be set up with HTTPS access | 1. Attempt to clone using `git clone https://server/repo.git`.<br>2. Enter valid credentials. | Clone operation should complete successfully. |
| **TC-10** | Invalid Credentials Test | Git server with authentication enabled | 1. Attempt to clone using incorrect credentials. | Authentication should fail with an appropriate error message. |
| **TC-11** | Conflict Resolution Test | Same file modified by multiple clients | 1. Modify the same file in two separate clients.<br>2. Attempt to push changes from both clients.<br>3. Resolve merge conflicts. | Merge conflict should be detected and resolved. |
| **TC-12** | Verify Git Client Container Connectivity to Git Server | Git client container must be running and accessible | 1. Ping the Git server container from the client container.<br>2. Verify that the Git client can reach the Git server. | Client successfully connects to the Git server without network issues. |
| **TC-13** | Verify File Permissions on Server Repository | Git repository must exist on server | 1. Check file permissions on the Git repository directory on the server.<br>2. Ensure the Git user has read and write permissions for the repository. | Git user should have correct file permissions to read/write on the repository. |
| **TC-14** | Verify Git Client Cloning with Submodules | Git repository with submodules should be available | 1. From the Git client, run `git clone --recurse-submodules user@server:/repo.git`.<br>2. Check if submodules are cloned successfully. | Submodules should be cloned correctly along with the main repository. |
| **TC-15** | Test Large File Push | Git server should support LFS (Large File Storage) | 1. Install Git LFS on the client.<br>2. Add a large file to the repository using `git lfs track <large-file>`.<br>3. Commit and push the changes.<br>4. Verify large file is successfully pushed to the server. | Large file should be pushed to the server successfully using Git LFS. |
| **TC-16** | Verify Commit History | Git repository must have several commits | 1. On the client, run `git log`.<br>2. Verify that the commit history is displayed correctly. | Commit history should be displayed accurately, including commit messages and dates. |
| **TC-17** | Verify Remote Branch Listing | Remote repository with multiple branches | 1. Run `git branch -r` from the client.<br>2. Check if the remote branches are listed correctly. | Remote branches should be listed without errors. |
| **TC-18** | Verify Git Merge Operation | Two branches with changes that can be merged | 1. Checkout to a new branch on the client.<br>2. Make changes and commit them.<br>3. Checkout to the main branch and merge the new branch.<br>4. Verify that the merge is successful. | Merge operation should complete successfully without conflicts. |
| **TC-19** | Verify Git Tagging | Git repository must have tags | 1. Run `git tag v1.0` on the client.<br>2. Push tags with `git push origin --tags`.<br>3. Verify the tag is pushed successfully on the server. | Tag should be created and pushed successfully. |
| **TC-20** | Verify Git Pull with Rebase | Remote repository has diverged commits | 1. Run `git pull --rebase origin main` from the client.<br>2. Verify that changes are applied with rebase instead of merge. | Changes should be fetched and rebased correctly. |
| **TC-21** | Test Git Client on Different Platforms | Git server and repository must be running | 1. Run Git client on different platforms (Linux, macOS, Windows).<br>2. Verify that the client can interact with the Git server seamlessly on all platforms. | Git client should work consistently across different platforms without issues. |
| **TC-22** | Verify Git Push with Large File (Non-LFS) | Large file added to repository without Git LFS | 1. Add a large file to the repository (e.g., > 100 MB).<br>2. Try to push the file to the server.<br>3. Verify if the push operation fails or succeeds based on server settings. | Large file should be rejected if not using Git LFS, or fail if the server doesn’t allow large file pushes. |
| **TC-23** | Test Git Client with Proxy Configuration | Proxy server must be configured | 1. Set up proxy settings for Git client.<br>2. Try to clone a repository through the proxy.<br>3. Verify that the operation succeeds or fails based on proxy settings. | Git client should be able to connect through the proxy server without issues. |
| **TC-24** | Test Git Server with Firewall Rules | Git server should have firewall rules in place | 1. Set up firewall rules to allow only certain ports (e.g., 22 for SSH, 443 for HTTPS).<br>2. Attempt to access the server using other ports.<br>3. Verify that access is denied for unauthorized ports. | Only authorized ports should be accessible, and others should be blocked. |
| **TC-25** | Test Git Commit with Emoji in Commit Message | Git server must support Unicode characters | 1. Run `git commit -m "Initial commit 🚀"` on the client.<br>2. Push the commit to the server.<br>3. Verify that the commit message with the emoji is pushed successfully. | Commit with emoji should be displayed correctly on the server. |

## 6. Test Execution
- Test execution will be performed in a controlled environment.
- Each test case will be executed, and results will be documented.
- Issues encountered will be logged and addressed.

## 7. Test Completion Criteria
- All test cases must be executed.
- Major and critical defects must be resolved.
- Communication between Git client and server should be seamless.

## 8. Summary
This test plan ensures that the Git client-server communication is functional, secure, and reliable using Docker-hosted environments. All necessary test cases are included to validate expected behavior, security measures, and failure handling mechanisms.

