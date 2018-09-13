#!/usr/bin/env python3
import os
import xml.etree.ElementTree as ET
from collections import defaultdict
import argparse
from urllib.request import urlopen
import json
import urllib.parse
from mvn_dep_updater.data.dependency import Dependency
from mvn_dep_updater.data.project import Project


def get_last_version_from_apache_archiva():
    data = 'Basic ZGVwbG95OmRlcGxveTE4MTg='
    header = {'Authorization': data}
    header['Referer'] = 'http://10.0.0.189:8080'
    header['Content-Type'] = 'application/json'

    url3 = 'http://10.0.0.189:8080/restServices/archivaServices/browseService/artifacts/jvaos-releases'
    urlArtifact = urllib.request.Request(url3, headers=header)
    readArtifact = urllib.request.urlopen(urlArtifact)
    artifactData = json.load(readArtifact)
    # print(artifactData)
    projectNameMapLastVersionFromApi = {}
    for i in range(len(artifactData)):
        projectNameMapLastVersionFromApi[artifactData[i].get('artifactId')] = None

    for i in projectNameMapLastVersionFromApi.keys():
        if i != 'JVAOSServiceClient':
            url2 = 'http://10.0.0.189:8080/restServices/archivaServices/browseService/versionsList/com.infodif.jvaos/' + i + '/?repositoryId=jvaos-releases'
            urlVersions = urllib.request.Request(url2, headers=header)
            readVersions = urllib.request.urlopen(urlVersions)
            versionData = json.load(readVersions)
            projectNameMapLastVersionFromApi[i] = versionData.get('versions')[len(versionData.get('versions')) - 1]
        else:
            url2 = 'http://10.0.0.189:8080/restServices/archivaServices/browseService/versionsList/com.infodif.jvaos.client/' + i + '/?repositoryId=jvaos-releases'
            urlVersions = urllib.request.Request(url2, headers=header)
            readVersions = urllib.request.urlopen(urlVersions)
            versionData = json.load(readVersions)
            projectNameMapLastVersionFromApi[i] = versionData.get('versions')[len(versionData.get('versions')) - 1]
    return projectNameMapLastVersionFromApi

def search_for_project_path(path):
    projects = {}

    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith("pom.xml"):
                namespaces = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
                tree = ET.parse(os.path.join(root, file))
                current_root = tree.getroot()
                project_path = None
                project_artifact_id = None
                project_version = None

                #find and set parent project id

                for d in current_root.findall("xmlns:artifactId", namespaces=namespaces):
                    project_artifact_id = d.text
                    project_path = os.path.join(root, file)
                    dependency_map = {}

                for xml_dependency in current_root.findall(".//xmlns:dependency", namespaces=namespaces):
                    dependencyArtifactId = xml_dependency.find(".//xmlns:artifactId", namespaces=namespaces).text
                    dependency_version_variable_name = None
                    if xml_dependency.find(".//xmlns:version", namespaces=namespaces) is not None:
                        version = xml_dependency.find(".//xmlns:version", namespaces=namespaces).text
                        dependency_version_variable_name = version[2:(len(version) - 1)]
                    dependency = Dependency(dependencyArtifactId, dependency_version_variable_name)

                    dependency_map[dependencyArtifactId] = dependency

                for xml_project_version in current_root.findall("xmlns:version", namespaces=namespaces):
                    project_version = xml_project_version.text[:len(xml_project_version.text) - 9]

                project = Project(project_artifact_id, project_version, project_path, dependency_map)
                projects[project_artifact_id] = project

    for project in projects.values():
        dependency_ids = list(project.dependencies.keys())
        projects[project.parent_id].add_child_project(project)
        for dependency_id in dependency_ids:
            if dependency_id not in projects.keys():
                del project.dependencies[dependency_id]

    return projects



def is_client_version_compatible(requestVersion, minClientVersion):
    requestVersion = [int(i) for i in requestVersion.split('.')]
    minClientVersion = [int(i) for i in minClientVersion.split('.')]

    minLen = len(requestVersion) if len(requestVersion) < len(minClientVersion) else len(minClientVersion)

    for i in range(minLen):
        if (minClientVersion[i] > requestVersion[i]):
            return False
        elif minClientVersion[i] < requestVersion[i]:
            return True
    if len(minClientVersion) > len(requestVersion):
        for minLen in range(len(minClientVersion)):
            if minClientVersion[i] != 0:
                return False
    return True


def updating_projects(projects,updatingList,projectNameMapLastVersionFromApi):
    for updaterProject in updatingList: #type(updaterProject ---> Project)
        for project in projects.values():
            isUpdatedNeeed = False
            if type(project.dependencies) == dict:
                if updaterProject.project_id in project.dependencies.keys():
                    namespaces = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
                    tree = ET.parse(project.path)
                    roots = tree.getroot()
                    # check if parent needs update and set isUpdateNeeded True.

                    for property in roots.findall(".//xmlns:properties", namespaces=namespaces):
                        if property.find(".//xmlns:" + project.dependencies[updaterProject.project_id].dependecy_version, namespaces=namespaces) != None:
                            if is_client_version_compatible(projectNameMapLastVersionFromApi[updaterProject.project_id],
                                                            updaterProject.project_version):
                                # project.projectVersion = compareProject.projectVersion
                                property.find(".//xmlns:" + project.dependencies[updaterProject.project_id].dependecy_version,
                                       namespaces=namespaces).text = projectNameMapLastVersionFromApi[updaterProject.project_id]
                                ET.register_namespace('', "http://maven.apache.org/POM/4.0.0")
                                tree.write(project.path, xml_declaration=True, encoding='utf-8', method='xml')
                                isUpdatedNeeed = True
                    del project.dependencies[updaterProject.project_id]
            if isUpdatedNeeed:
                updateProjectInGitlabAndBuild(project)

def build_dependency_tree(projects):
    for project in projects.values():
        for dependency in project.dependencies.values():
            for sub_dependency in projects[dependency.dependecy_id].dependencies.values():
                dependency.add_dependency(sub_dependency)

def print_projects(projects):
    for project in projects.values():
        print("Id: "+project.project_id)
        print("Version: "+project.project_version)
        print("Path: "+ project.path)
        for dependency in project.dependencies.values():
            print("------- dependency: " + dependency.dependecy_id + " ----dependency version: " + dependency.dependecy_version)

def set_level_of_projects(projects, dependency, level):
    if (level > projects[dependency.dependecy_id].level):
        projects[dependency.dependecy_id].level = level
    if len(dependency.dependencies.values()) == 0:
        return
    else:
        for sub_dependency in dependency.dependencies.values():
            set_level_of_projects(projects, sub_dependency, level + 1)

def create_update_list(projects):
    for project in projects.values():
        for dependency in project.dependencies.values():
            set_level_of_projects(projects, dependency, 1)
    updatingList = sorted(projects.values(),key=lambda kv : kv.level,reverse=True)
    return updatingList

def job(path, hostname, token):
    os.chdir(path)

    projects = search_for_project_path(path)

    build_dependency_tree(projects)

    updatingList = create_update_list(projects)

    for project in updatingList:
        print(project.project_id)

    # projectNameMapLastVersionFromApi = get_last_version_from_apache_archiva()
    #
    # updating_projects(projects,updatingList,projectNameMapLastVersionFromApi)

def updateProjectInGitlabAndBuild(project):
    #     os.chdir("D:\projects\maven-dependency-updater")
    #     repo = Repo("D:\projects\maven-dependency-updater")
    #     repo.git.checkout('master')
    #     repo.git.add('main.py', 'pom.xml')
    #     repo.git.commit('-m', 'Testing')
    #     repo.git.pull('yerel-yedek', 'master')
    #     namespaces = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
    #     tree = ET.parse('pom.xml')
    #     roots = tree.getroot()
    #     for d in roots.findall("xmlns:artifactId", namespaces=namespaces):
    #         for project in projectsWithFeature:
    #             if project.projectName == d.text:
    #                 a = roots.find("xmlns:version", namespaces=namespaces).text
    #                 if isClientVersionCompatible(a[:len(a) - 9], project.projectVersion):
    #                     project.projectVersion = a[:len(a) - 9]
    pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dir', dest='path', help='Directory if app is used without current working direcotry', required=False)
    parser.add_argument('-H', '--hostname', dest='hostname', help='Hostname or IP address of gitlab', required=True)
    parser.add_argument('-t', '--token', dest='token', help='Gitlab access token', required=True)
    result = parser.parse_args()

    if result is not None:
        path = os.getcwd()
        if result.path is not None:
            path = result.path
        job(path, result.hostname, result.token)


if __name__ == "__main__":
    main()
