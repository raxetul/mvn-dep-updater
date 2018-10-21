#!/usr/bin/env python3
import os
import time
import xml.etree.ElementTree as ET
import gitlab
import argparse
from urllib.request import urlopen
import json
import urllib.parse

from git import Repo

from mvn_dep_updater.data.dependency import Dependency
from mvn_dep_updater.data.project import Project
import base64

sleep_time = 3  # TODO: Magic Number

def get_last_version_from_apache_archiva(project, hostName, idPassword, repoId):
    idPassword = base64.b64encode(bytes(idPassword,'utf-8'))
    data = 'Basic '+idPassword.decode('ascii')
    header = {'Authorization': data}
    header['Referer'] = hostName
    header['Content-Type'] = 'application/json'

    if project.group_id != None :
        url2 = hostName+'restServices/archivaServices/browseService/versionsList/'+project.group_id+'/' + project.project_id + '/?repositoryId='+repoId
        urlVersions = urllib.request.Request(url2, headers=header)
        readVersions = urllib.request.urlopen(urlVersions)
        versionData = json.load(readVersions)
        versions = versionData.get('versions')
        if len(versions) > 0:
            return versions[-1] # last version
        else:
            return None


def search_for_project_path(path):
    projects = {}

    for projectRootPath, dirs, files in os.walk(path):
        for file in files:
            if file.endswith("pom.xml"):
                namespaces = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
                tree = ET.parse(os.path.join(projectRootPath, file))
                current_root = tree.getroot()
                project_artifact_id = None
                project_version = None
                parent_groupId = None
                #find and set parent project id
                if current_root.find("xmlns:groupId", namespaces=namespaces)!=None:
                    parent_groupId = current_root.find("xmlns:groupId", namespaces=namespaces).text

                for d in current_root.findall("xmlns:artifactId", namespaces=namespaces):
                    project_artifact_id = d.text
                    dependency_map = {}

                for parent in current_root.findall(".//xmlns:parent", namespaces=namespaces):
                    parent_name = parent.find(".//xmlns:artifactId", namespaces=namespaces).text
                    parent_version = parent.find(".//xmlns:version", namespaces=namespaces).text
                    parent_groupId = parent.find(".//xmlns:groupId",namespaces=namespaces).text
                    dependency = Dependency(parent_name, '', parent_version, True)
                    dependency_map[parent_name] = dependency

                for xml_dependency in current_root.findall(".//xmlns:dependency", namespaces=namespaces):
                    dependencyArtifactId = xml_dependency.find(".//xmlns:artifactId", namespaces=namespaces).text

                    # TODO: var_value and variable_name will be arranged if a propoert is not used for a version value
                    var_value = None
                    variable_name = None

                    if xml_dependency.find(".//xmlns:version", namespaces=namespaces) is not None:
                        version = xml_dependency.find(".//xmlns:version", namespaces=namespaces).text
                        if version.startswith('${'):
                            variable_name = version[2:(len(version) - 1)]
                            for property in current_root.findall(".//xmlns:properties", namespaces=namespaces):
                                element = property.find(".//xmlns:" + variable_name, namespaces=namespaces)
                                if element is not None:
                                    var_value = element.text
                        else:
                            var_value = version


                    dependency = Dependency(dependencyArtifactId, variable_name, var_value)
                    dependency_map[dependencyArtifactId] = dependency

                for xml_project_version in current_root.findall("xmlns:version", namespaces=namespaces):
                    project_version = xml_project_version.text[:len(xml_project_version.text) - 9]

                project = Project(project_artifact_id, project_version, projectRootPath, dependency_map, parent_groupId)
                projects[project_artifact_id] = project

    for project in projects.values():
        dependency_ids = list(project.dependencies.keys())
        for dependency_id in dependency_ids:
            if dependency_id not in projects.keys():
                del project.dependencies[dependency_id]

    return projects


def is_update_needed(versionInMvnRepo, currentDependencyVersion):
    versionInMvnRepo = [int(i) for i in versionInMvnRepo.split('.')]
    currentDependencyVersion = [int(i) for i in currentDependencyVersion.split('.')]

    minLen = len(versionInMvnRepo) if len(versionInMvnRepo) < len(currentDependencyVersion) else len(currentDependencyVersion)

    for i in range(minLen):
        if (currentDependencyVersion[i] > versionInMvnRepo[i]):
            return False
        elif currentDependencyVersion[i] < versionInMvnRepo[i]:
            return True
    if len(currentDependencyVersion) > len(versionInMvnRepo):
        for minLen in range(len(currentDependencyVersion)):
            if currentDependencyVersion[i] != 0:
                return False
    else:
        if len(currentDependencyVersion) == len(versionInMvnRepo):
            return False
    return True


def update_projects(projects, updatingList, hostName, archiva_token, repoId, server_addr, token):
    gitlab_server = gitlab.Gitlab(server_addr, private_token=token)
    gitlab_projects = gitlab_server.projects.list(all=True)

    for toBeUpdatedProject in updatingList: #type(updaterProject ---> Project)
        gitlab_project = None
        for gp in gitlab_projects:
            if gp.name == toBeUpdatedProject.project_id:
                gitlab_project = gp
                break

        print('Checking: ' + toBeUpdatedProject.project_id)
        update_needed = False
        os.chdir(toBeUpdatedProject.path)
        local_repo = Repo(toBeUpdatedProject.path)
        local_repo.git.checkout('master')
        local_repo.git.pull()
        for branch in local_repo.branches:
            if branch.name == 'automatic/update/pom':  # TODO: Magic String
                local_repo.delete_head('automatic/update/pom', '-D')
                print('update/pom branch is deleted, a new one will be created')
        local_repo.create_head('automatic/update/pom')
        local_repo.git.checkout('automatic/update/pom')

        namespaces = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
        tree = ET.parse(toBeUpdatedProject.path + "/pom.xml", )
        roots = tree.getroot()

        for dependency in toBeUpdatedProject.dependencies.values():
            print('\tDependency: ' + dependency.id)
            dependencyProject = projects[dependency.id]
            dependencyLatestVersion = get_last_version_from_apache_archiva(dependencyProject, hostName, archiva_token, repoId)

            # check if dependency is parent or not
            # version = ""
            if is_update_needed(dependencyLatestVersion, dependency.version):
                update_needed = True
                print('\t\tUpdate found=> Current Version: ' + dependency.version + '\t  /\tIn Repo Version: ' + dependencyLatestVersion)
                if dependency.isParent:
                        for parent_dependency in roots.findall(".//xmlns:parent", namespaces=namespaces):
                            element = parent_dependency.find(".//xmlns:version", namespaces=namespaces)
                            element.text = dependencyLatestVersion
                else:
                    if dependency.var_name is not None:
                        for xml_property in roots.findall(".//xmlns:properties", namespaces=namespaces):
                            element = xml_property.find(".//xmlns:" + dependency.var_name, namespaces=namespaces)
                            if element is not None:
                                element.text = dependencyLatestVersion
                                break
                    else:
                        # version =  dependency.version
                        # TODO: Needs fix for none property dependency version values in here
                        pass

        if update_needed:
            ET.register_namespace('', 'http://maven.apache.org/POM/4.0.0')
            tree.write(toBeUpdatedProject.path + "/pom.xml", xml_declaration=True, encoding='utf-8', method='xml')
            commit_and_push_project(local_repo)
            time.sleep(sleep_time)
            merge_and_deploy_project(gitlab_project)


def build_dependency_tree(projects):
    for project in projects.values():
        for dependency in project.dependencies.values():
            for sub_dependency in projects[dependency.id].dependencies.values():
                dependency.add_dependency(sub_dependency)


def print_projects(projects):
    for project in projects.values():
        print("Id: "+project.project_id)
        print("Current Version in repo: "+project.project_version)
        print("Path: "+ project.path)
        for dependency in project.dependencies.values():
            print("------- dependency: " + dependency.dependecy_id + " ----dependency version: " + dependency.dependecy_version)


def set_level_of_projects(projects, dependency, level):
    if (level > projects[dependency.id].level):
        projects[dependency.id].level = level
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


def job(path, hostName, archiva_token, repoId, server, token):
    os.chdir(path)

    projects = search_for_project_path(path)

    build_dependency_tree(projects)

    orderedUpdateList = create_update_list(projects)

    # projectNameMapLastVersionFromApi = get_last_version_from_apache_archiva(projects, hostName, token, repoId)

    update_projects(projects, orderedUpdateList, hostName, archiva_token, repoId, server, token)


def commit_and_push_project(local_repo):
    local_repo.git.add('pom.xml')
    local_repo.git.commit('-m', 'Dependencies and parent of the project in pom file are updated.')
    for remote in local_repo.remotes:
        # TODO: Magic String
        if remote.name == 'origin':
            remote.push(refspec='automatic/update/pom:automatic/update/pom')
            local_repo.git.checkout('master')
            # repo.delete_head('automatic/update/pom')
            break
    # TODO: checkout master


def wait_for_pipeline_to_finish(gitlab_project):
    running_pipeline_ids = set()

    # fill running pipeline set
    for pipeline in gitlab_project.pipelines.list(page=1, per_page=10):
        if pipeline.status == 'running' and pipeline.id not in running_pipeline_ids:
            running_pipeline_ids.add(pipeline.id)

    if len(running_pipeline_ids) == 0:
        print('Error: there should be a running pipeline')
        return False

    # remove pipelines from pipeline set until all finished
    while True:
        time.sleep(sleep_time)  # TODO: Magic Number
        for pipeline_id in running_pipeline_ids.copy():
            pipeline = gitlab_project.pipelines.get(pipeline_id)
            if pipeline.status == 'success':
                running_pipeline_ids.remove(pipeline.id)
            if pipeline.status == 'failed':
                exit(1)
        for pipeline in gitlab_project.pipelines.list(page=1, per_page=10):
            if pipeline.status == 'running' and pipeline.id not in running_pipeline_ids:
                running_pipeline_ids.add(pipeline.id)
        if len(running_pipeline_ids) == 0:
            break
    return True

def merge_and_deploy_project(gitlab_project):

    # find and wait for build of last push
    if not wait_for_pipeline_to_finish(gitlab_project):
        # exit(1)
        pass

    # no more running pipeline create merge request and accept it # TODO: Magic String
    mr = gitlab_project.mergerequests.create({'source_branch': 'automatic/update/pom',
                                              'target_branch': 'master',
                                              'title': 'Automatic merge for dependency version update'})
    time.sleep(1)  # TODO: Magic Number
    mr.merge()
    time.sleep(1)

    # deploy
    job_should_be_run = None
    job_found = False
    for pipeline in gitlab_project.pipelines.list(page=1, per_page=5):  # find first deploy
        for job_to_do in pipeline.jobs.list(page=1, per_page=5):
            if job_to_do.name == 'job_deploy':  # TODO: Magic String
                job_should_be_run = gitlab_project.jobs.get(job_to_do.id, lazy=True)
                job_found = True
                break
        if job_found:
            break
    job_should_be_run.play()

    time.sleep(1)

    # get running pipelines after job_deploy
    wait_for_pipeline_to_finish(gitlab_project)

    update_branch = gitlab_project.branches.get('automatic/update/pom')
    if update_branch is not None:
        update_branch.delete()
    pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dir', dest='path', help='Directory if app is used without current working direcotry', required=False)
    parser.add_argument('-H', '--host', dest='hostname', help='Hostname or IP address of gitlab with port ex: 192.168.1.2:8080', required=True)
    parser.add_argument('-a', '--archiva-id-pw', dest='idPw', help='Apache Archiva authorization in form of user:password', required=True)
    parser.add_argument('-r', '--repo-id', dest='repoId', help='Apache Archiva access repository id.', required=True)
    parser.add_argument('-s', '--gitlab-server', dest='server', help='Gitlab server address including port. Ex: http://192.168.1.3:9090', required=True)
    parser.add_argument('-t', '--token', dest='token', help='Gitlab access token', required=True)
    result = parser.parse_args()

    if result is not None:
        path = os.getcwd()
        if result.path is not None:
            path = result.path
        job(path, result.hostname, result.idPw, result.repoId, result.server, result.token)


if __name__ == "__main__":
    main()
