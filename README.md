#Maven Dependency Updater
## About
Aim of this project is to automatically find and update version of local dependencies with:
- Gitlab integration as VCS
- Apache Archiva integration for maven artifact repository

Script finds out the local dependencies, categorize them according to deepest dependency chain, then starts updating from deepest one.
This script can not update external dependencies according to their latest versions.

!Dependency versions should be defined as PROPERTY!

## Installation
Currently not added to pypi.org so project can be installed with pip locally in the root of the project:

`` pip install .``

or for user only:

``pip install --user .``

## Dependencies
- GitPython
- python-gitlab

Msys2 users or who uses python2 and python3 at the same time may define the version of pip via

``pip3 `` or ``pip2`` instead of ``pip``


## Usage
In your project root:

``mvn-dep-updater -H GITLAB_HOST_NAME_OR_IP:PORT -a ARCHIVA_USER_NAME:PASSWORD -r REPOID_IN_ARCHIVA_REPO -s ARCHIVA_HOST_NAME_OR_IP:PORT -t GITLAB_ACCES_TOKEN``
    
or in different path:

``mvn-dep-updater -d PROJECT_ROOT_PATH -H GITLAB_HOST_NAME_OR_IP:PORT -a ARCHIVA_USER_NAME:PASSWORD -r REPOID_IN_ARCHIVA_REPO -s ARCHIVA_HOST_NAME_OR_IP:PORT -t GITLAB_ACCES_TOKEN``



## TODO
- [ ] Object oriented refactoring is needed
- [ ] For current code deploy job name is **job_deploy** for gitlab, this should be parametric
- [ ] Yml saved config for project
- [ ] Project should be added to pypi.org
- [ ] Gitlab and Apache Archiva servers should be changeable to alternatives 


