#Maven Dependency Updater
Aim of this project is to automatically find and update version of local dependencies with:
- Gitlab integration as VCS
- Apache Archiva integration for maven artifact repository

Script finds out the local dependencies, categorize them according to deepest dependency chain, then starts updating from deepest one.
This script can not update external dependencies according to their latest versions.

