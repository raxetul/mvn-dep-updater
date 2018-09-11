#!/usr/bin/env python3
import os
import xml.etree.ElementTree as ET
from collections import defaultdict
import argparse

from mvn_dep_updater.data.dependency import Dependency
from mvn_dep_updater.data.path_tree import PathTree
from mvn_dep_updater.data.project import Project


def get_project_by_name(name, projectsWithFeature):
    for project in projectsWithFeature:
        if name == project.projectName:
            return project


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
        for dependency_id in dependency_ids:
            if dependency_id not in projects.keys():
                del project.dependencies[dependency_id]

    return projects


def add_base_project_updating_list(baseProjects, updatingList):
    for project in baseProjects:
        updatingList.append(project)


def get_base_projects(artifactIdToPathMap, baseProjectList, dependencyMap):
    for project in artifactIdToPathMap.keys():
        if dependencyMap.get(project) == None:
            baseProjectList.append(project)


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


def create_project_list_with_features(dependencyMap, artifactIdMap, projectWithFeatures, specificVersion,
                                      projectNameAndPath):
    count = 0

    for project_name in projectNameAndPath.keys():
        if project_name in dependencyMap.keys():
            newDict = dict(zip(artifactIdMap.get(project_name), dependencyMap.get(project_name)))
            newProject = Project(project_name, newDict, specificVersion[count])  # NEW PROJECT
            count += 1
            projectWithFeatures.append(newProject)
        else:
            newProject = Project(project_name, None, specificVersion[count])  # NEW PROJECT
            count += 1
            projectWithFeatures.append(newProject)


def find_paths(project, baseProjectList, projectsWithFeature, balancedPathList, balancedPathLists):
    if project in baseProjectList:
        balancedPathLists.append(balancedPathList.copy())
        return
    else:
        getProject = get_project_by_name(project, projectsWithFeature)
        for dependency in getProject.artifactIdMapVersion.keys():
            if dependency not in baseProjectList:
                balancedPathList.append(dependency)
            find_paths(dependency, baseProjectList, projectsWithFeature, balancedPathList, balancedPathLists)
            balancedPathList.clear()


def create_tree(artifactIdToPathMap, baseProjects, projectsWithFeature, allTrees):
    balancedPathLists = []
    balancedPathList = []
    x = 0
    for project in artifactIdToPathMap.keys():
        find_paths(project, baseProjects, projectsWithFeature, balancedPathList, balancedPathLists)
        for i in balancedPathLists:
            if x < len(i):
                x = len(i)
            tree = PathTree(project, x, balancedPathLists.copy())
        allTrees.append(tree)
        x = 0
        balancedPathLists.clear()
        balancedPathList.clear()


def updating_projects(updatingList, artifactIdToPathMap, projectsWithFeature, commitMessageList):
    for pName in updatingList:
        compareProject = get_project_by_name(pName, projectsWithFeature)
        for project in projectsWithFeature:
            if type(project.artifactIdMapVersion) == dict:
                if pName in project.artifactIdMapVersion.keys():
                    namespaces = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
                    tree = ET.parse(artifactIdToPathMap.get(project.projectName))
                    roots = tree.getroot()
                    for d in roots.findall(".//xmlns:properties", namespaces=namespaces):
                        if d.find(".//xmlns:" + project.artifactIdMapVersion.get(pName), namespaces=namespaces) != None:
                            if is_client_version_compatible(compareProject.projectVersion,
                                                            d.find(
                                                                ".//xmlns:" + project.artifactIdMapVersion.get(pName),
                                                                namespaces=namespaces).text):
                                # project.projectVersion = compareProject.projectVersion
                                d.find(".//xmlns:" + project.artifactIdMapVersion.get(pName),
                                       namespaces=namespaces).text = compareProject.projectVersion
                                ET.register_namespace('', "http://maven.apache.org/POM/4.0.0")
                                tree.write(artifactIdToPathMap.get(project.projectName), xml_declaration=True,
                                           encoding='utf-8', method='xml')


def update_tree(allTree, deletingNode):
    for nodes in allTree:
        for nodeInPath in nodes.paths:
            for node in nodeInPath:
                if node == deletingNode.nameOfOwner:
                    nodeInPath.remove(node)
    for nodes in allTree:
        if nodes.nameOfOwner == deletingNode.nameOfOwner:
            allTree.remove(deletingNode)
    for nodes in allTree:
        x = 0
        for nodeInPath in nodes.paths:
            if len(nodeInPath) >= x:
                x = len(nodeInPath)
        nodes.maxLen = x


def delete_base_nodes_on_tree(allTrees, baseProjects):
    for project in baseProjects:
        for nodes in allTrees:
            for nodeInPath in nodes.paths:
                for node in nodeInPath:
                    if node == project:
                        nodeInPath.remove(node)
    for project in baseProjects:
        for nodes in allTrees:
            if nodes.nameOfOwner == project:
                allTrees.remove(nodes)


def get_path_of_owner_by_name(allTree, nameOfNode):
    for node in allTree:
        if node.nameOfOwner == nameOfNode:
            return node


def find_leaf_and_update_projects(originNode, updatingList, allTree):
    if originNode != None:
        if originNode.maxLen == 0:
            updatingList.append(originNode.nameOfOwner)
            update_tree(allTree, originNode)
            if len(allTree) > 0:
                find_leaf_and_update_projects(allTree[0], updatingList, allTree)
        else:
            for searchNode in originNode.paths:
                for matchNode in searchNode:
                    project = get_path_of_owner_by_name(allTree, matchNode)
                    find_leaf_and_update_projects(project, updatingList, allTree)


def get_reverse_or_tree(allTree):
    for node in allTree:
        for i in node.paths:
            i.reverse()


def print_updating_list(updatingList):
    for i in updatingList:
        print(i)


def print_paths(allTrees):
    for i in allTrees:
        string = ''
        for x in i.paths:
            for c in x:
                string += c
                string += '->'
            string = string[:len(string) - 2]
            print('{0}, {1}, {2}'.format(i.nameOfOwner, 'has path', string))
            string = ''
        print(i.maxLen)

def print_projects(projects):
    for project in projects.values():
        print(project.project_id)
        for dependency in project.dependencies.values():
            print("------- dependency: " + dependency.dependecy_id + " - " + dependency.dependecy_version)

def job(path):
    os.chdir(path)

    dependencyMap = defaultdict(list)
    mapArtifactId = defaultdict(list)

    projectsWithFeature = []
    mapSpecificVersion = []
    updatingList = []
    baseProjects = []
    allTrees = []
    commitMessageList = []

    projects = search_for_project_path(path)

    print_projects(projects)

    # create_project_list_with_features(dependencyMap, mapArtifactId, projectsWithFeature, mapSpecificVersion,
    #                                   artifactIdToPathMap)
    #
    # create_tree(artifactIdToPathMap, baseProjects, projectsWithFeature, allTrees)
    #
    # add_base_project_updating_list(baseProjects, updatingList)
    #
    # get_reverse_or_tree(allTrees)
    #
    # delete_base_nodes_on_tree(allTrees, baseProjects)
    #
    # find_leaf_and_update_projects(allTrees[0], updatingList, allTrees)
    #
    # #tryGitPython(projectsWithFeature)
    #
    # updating_projects(updatingList, artifactIdToPathMap, projectsWithFeature, commitMessageList)

    # def tryGitPython(projectsWithFeature):
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', dest='path', help='Projects root dir', required=False)
    result = parser.parse_args()
    if result is not None:
        path = os.getcwd()
        if result.path is not None:
            path = result.path
        job(path)


if __name__ == "__main__":
    main()
