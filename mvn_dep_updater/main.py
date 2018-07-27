import os
import xml.etree.ElementTree as ET
from collections import defaultdict
import argparse
from mvn_dep_updater.data.path_tree import PathTree
from mvn_dep_updater.data.project import Project

def get_project_by_name(name, projectsWithFeature):
    for project in projectsWithFeature:
        if name == project.projectName:
            return project


def search_for_project_path(projectNameAndPaths):
    for root, dirs, files in os.walk(os.getcwd()):
        for file in files:
            if file.endswith("pom.xml"):
                namespaces = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
                tree = ET.parse(os.path.join(root, file))
                roots = tree.getroot()
                for d in roots.findall("xmlns:artifactId", namespaces=namespaces):
                    projectNameAndPaths[d.text] = os.path.join(root, file)


def add_base_project_updating_list(baseProjects, updatingList):
    for project in baseProjects:
        updatingList.append(project)


def map_projects(projectNameAndPath, dependencyMap, artifactIdMap, specificVersion):
    for paths in projectNameAndPath.values():
        namespaces = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
        tree = ET.parse(paths)
        roots = tree.getroot()
        for d in roots.findall(".//xmlns:dependency", namespaces=namespaces):
            artifactId = d.find(".//xmlns:artifactId", namespaces=namespaces).text
            if artifactId in projectNameAndPath.keys():
                for fileName in roots.findall("xmlns:artifactId", namespaces=namespaces):
                    version = d.find(".//xmlns:version", namespaces=namespaces).text
                    dependencyMap[fileName.text].append(version[2:(len(version) - 1)])
                    artifactIdMap[fileName.text].append(artifactId)
        for sVersion in roots.findall("xmlns:version", namespaces=namespaces):
            specificVersion.append(sVersion.text[:len(sVersion.text) - 9])


def get_base_projects(projectNameAndPath, baseProjectList, dependencyMap):
    for project in projectNameAndPath.keys():
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

    for project in projectNameAndPath.keys():
        if project in dependencyMap.keys():
            newDict = dict(zip(artifactIdMap.get(project), dependencyMap.get(project)))
            newProject = Project(project, newDict, specificVersion[count])
            count += 1
            projectWithFeatures.append(newProject)
        else:
            newProject = Project(project, None, specificVersion[count])
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


def create_tree(projectNameAndPath, baseProjects, projectsWithFeature, allTrees):
    balancedPathLists = []
    balancedPathList = []
    x = 0
    for project in projectNameAndPath.keys():
        find_paths(project, baseProjects, projectsWithFeature, balancedPathList, balancedPathLists)
        for i in balancedPathLists:
            if x < len(i):
                x = len(i)
            tree = PathTree(project, x, balancedPathLists.copy())
        allTrees.append(tree)
        x = 0
        balancedPathLists.clear()
        balancedPathList.clear()


def updating_projects(updatingList, projectNameAndPath, projectsWithFeature, commitMessageList):
    for pName in updatingList:
        compareProject = get_project_by_name(pName, projectsWithFeature)
        for project in projectsWithFeature:
            if type(project.artifactIdMapVersion) == dict:
                if pName in project.artifactIdMapVersion.keys():
                    namespaces = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
                    tree = ET.parse(projectNameAndPath.get(project.projectName))
                    roots = tree.getroot()
                    for d in roots.findall(".//xmlns:properties", namespaces=namespaces):
                        if d.find(".//xmlns:" + project.artifactIdMapVersion.get(pName), namespaces=namespaces) != None:
                            if is_client_version_compatible(compareProject.projectVersion,
                                                            d.find(".//xmlns:" + project.artifactIdMapVersion.get(pName),
                                                                namespaces=namespaces).text):
                                # project.projectVersion = compareProject.projectVersion
                                d.find(".//xmlns:" + project.artifactIdMapVersion.get(pName),
                                       namespaces=namespaces).text = compareProject.projectVersion
                                ET.register_namespace('', "http://maven.apache.org/POM/4.0.0")
                                tree.write(projectNameAndPath.get(project.projectName), xml_declaration=True,
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


def job(path):

    os.chdir(path)

    dependencyMap = defaultdict(list)
    mapArtifactId = defaultdict(list)

    projectNameAndPath = {}

    projectsWithFeature = []
    mapSpecificVersion = []
    updatingList = []
    baseProjects = []
    allTrees = []
    commitMessageList = []

    search_for_project_path(projectNameAndPath)

    map_projects(projectNameAndPath, dependencyMap, mapArtifactId, mapSpecificVersion)

    get_base_projects(projectNameAndPath, baseProjects, dependencyMap)

    create_project_list_with_features(dependencyMap, mapArtifactId, projectsWithFeature, mapSpecificVersion,
                                      projectNameAndPath)

    create_tree(projectNameAndPath, baseProjects, projectsWithFeature, allTrees)

    add_base_project_updating_list(baseProjects, updatingList)

    get_reverse_or_tree(allTrees)

    delete_base_nodes_on_tree(allTrees, baseProjects)

    find_leaf_and_update_projects(allTrees[0], updatingList, allTrees)

    #tryGitPython(projectsWithFeature)

    updating_projects(updatingList, projectNameAndPath, projectsWithFeature, commitMessageList)



'''
def tryGitPython(projectsWithFeature):
    os.chdir("D:\projects\maven-dependency-updater")
    repo = Repo("D:\projects\maven-dependency-updater")
    repo.git.checkout('master')
    repo.git.add('main.py', 'pom.xml')
    repo.git.commit('-m', 'Testing')
    repo.git.pull('yerel-yedek', 'master')
    namespaces = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
    tree = ET.parse('pom.xml')
    roots = tree.getroot()
    for d in roots.findall("xmlns:artifactId", namespaces=namespaces):
        for project in projectsWithFeature:
            if project.projectName == d.text:
                a = roots.find("xmlns:version", namespaces=namespaces).text
                if isClientVersionCompatible(a[:len(a) - 9], project.projectVersion):
                    project.projectVersion = a[:len(a) - 9]

'''
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir',dest='path',help='Projects root dir', required=True)
    result = parser.parse_args()
    if result is not None:
        job(result.path)


if __name__ == "__main__":
    main()
