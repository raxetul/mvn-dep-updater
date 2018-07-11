import os
from git import Repo
import xml.etree.ElementTree as ET
from collections import defaultdict


class Project:
    def __init__(self, projectName, artifactIdMapVersion, projectVersion):
        self.projectName = projectName
        self.artifactIdMapVersion = artifactIdMapVersion
        self.projectVersion = projectVersion

class PathTree:
    def __init__(self, nameOfOwner, maxLen, paths):
        self.nameOfOwner = nameOfOwner
        self.maxLen = maxLen
        self.paths = paths

def getProjectByName(name, projectsWithFeature):
    for project in projectsWithFeature:
        if name == project.projectName:
            return project

def searchForProjectPath(projectNameAndPaths):
    os.chdir('Add direction')
    for root, dirs, files in os.walk(os.getcwd()):
        for file in files:
            if file.endswith("pom.xml"):
                namespaces = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
                tree = ET.parse(os.path.join(root, file))
                roots = tree.getroot()
                for d in roots.findall("xmlns:artifactId", namespaces=namespaces):
                    projectNameAndPaths[d.text] = os.path.join(root, file)

def addBaseProjectUpdatingList(baseProjects,updatingList):
    for project in baseProjects:
        updatingList.append(project)

def mapProjects(projectNameAndPath, dependencyMap, artifactIdMap, specificVersion):
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
            specificVersion.append(sVersion.text[:len(sVersion.text)-9])

def getBaseProjects(projectNameAndPath, baseProjectList, dependencyMap):
    for project in projectNameAndPath.keys():
        if dependencyMap.get(project) == None:
            baseProjectList.append(project)

def isClientVersionCompatible(requestVersion,minClientVersion):
    requestVersion = [int(i) for i in requestVersion.split('.')]
    minClientVersion = [int(i) for i in minClientVersion.split('.')]

    minLen = len(requestVersion) if len(requestVersion) < len(minClientVersion) else len(minClientVersion)

    for i in range(minLen):
        if(minClientVersion[i]>requestVersion[i]):
            return False
        elif minClientVersion[i] < requestVersion[i]:
            return True
    if len(minClientVersion)>len(requestVersion):
        for minLen in range(len(minClientVersion)):
            if minClientVersion[i]!=0:
                return False

    return True


def createProjectListWithFeatures(dependencyMap, artifactIdMap, projectWithFeatures, specificVersion, projectNameAndPath):
    count = 0

    for project in projectNameAndPath.keys():
        if project in dependencyMap.keys():
            newDict=dict(zip(artifactIdMap.get(project), dependencyMap.get(project)))
            newProject = Project(project,newDict,specificVersion[count])
            count += 1
            projectWithFeatures.append(newProject)
        else:
            newProject = Project(project, None , specificVersion[count])
            count += 1
            projectWithFeatures.append(newProject)

def findPaths(project, baseProjectList, projectsWithFeature, balancedPathList, balancedPathLists):
    if project in baseProjectList:
        balancedPathLists.append(balancedPathList.copy())
        return
    else:
        getProject = getProjectByName(project,projectsWithFeature)
        for dependency in getProject.artifactIdMapVersion.keys():
            if dependency not in baseProjectList:
                balancedPathList.append(dependency)
            findPaths(dependency, baseProjectList, projectsWithFeature, balancedPathList, balancedPathLists)
            balancedPathList.clear()

def createTree(projectNameAndPath, baseProjects, projectsWithFeature, allTrees):
    balancedPathLists = []
    balancedPathList = []
    x = 0
    for project in projectNameAndPath.keys():
        findPaths(project, baseProjects, projectsWithFeature, balancedPathList, balancedPathLists)
        for i in balancedPathLists:
            if x < len(i):
                x = len(i)
            tree = PathTree(project, x, balancedPathLists.copy())
        allTrees.append(tree)
        x = 0
        balancedPathLists.clear()
        balancedPathList.clear()

def updatingProjects(updatingList, projectNameAndPath, projectsWithFeature,commitMessageList):
    os.chdir("Add direction")
    for pName in updatingList:
        compareProject = getProjectByName(pName,projectsWithFeature)
        for project in projectsWithFeature:
            if type(project.artifactIdMapVersion)==dict:
                if pName in project.artifactIdMapVersion.keys():
                    namespaces = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
                    tree = ET.parse(projectNameAndPath.get(project.projectName))
                    roots = tree.getroot()
                    for d in roots.findall(".//xmlns:properties", namespaces=namespaces):
                            if d.find(".//xmlns:" + project.artifactIdMapVersion.get(pName),namespaces=namespaces)!=None:
                                if isClientVersionCompatible(compareProject.projectVersion,d.find(".//xmlns:" + project.artifactIdMapVersion.get(pName),namespaces=namespaces).text):
                                    #project.projectVersion = compareProject.projectVersion
                                    d.find(".//xmlns:" + project.artifactIdMapVersion.get(pName),namespaces=namespaces).text = compareProject.projectVersion
                                    ET.register_namespace('', "http://maven.apache.org/POM/4.0.0")
                                    tree.write(projectNameAndPath.get(project.projectName), xml_declaration=True, encoding='utf-8', method='xml')


def updateTree(allTree,deletingNode):
    for nodes in allTree:
        for nodeInPath in nodes.paths:
            for node in nodeInPath:
                if node==deletingNode.nameOfOwner:
                    nodeInPath.remove(node)
    for nodes in allTree:
        if nodes.nameOfOwner==deletingNode.nameOfOwner:
            allTree.remove(deletingNode)
    for nodes in allTree:
        x=0
        for nodeInPath in nodes.paths:
            if len(nodeInPath)>=x:
                x=len(nodeInPath)
        nodes.maxLen = x

def deleteBaseNodesOnTree(allTrees,baseProjects):
    for project in baseProjects:
        for nodes in allTrees:
            for nodeInPath in nodes.paths:
                for node in nodeInPath:
                    if node == project:
                        nodeInPath.remove(node)
    for project in baseProjects:
        for nodes in allTrees:
            if nodes.nameOfOwner==project:
                allTrees.remove(nodes)

def getPathOfOwnerByName(allTree,nameOfNode):
    for node in allTree:
        if node.nameOfOwner==nameOfNode:
            return node

def findLeafAndUpdateProjects(originNode,updatingList,allTree):
        if originNode != None:
            if originNode.maxLen ==0:
                updatingList.append(originNode.nameOfOwner)
                updateTree(allTree,originNode)
                if len(allTree)>0:
                    findLeafAndUpdateProjects(allTree[0],updatingList,allTree)
            else:
                for searchNode in originNode.paths:
                    for matchNode in searchNode:
                        project = getPathOfOwnerByName(allTree,matchNode)
                        findLeafAndUpdateProjects(project,updatingList,allTree)

def getReverseOfTree(allTree):
    for node in allTree:
        for i in node.paths:
            i.reverse()

def printUpdatingList(updatingList):
    for i in updatingList:
        print(i)

def printPaths(allTrees):
    for i in allTrees:
        string = ''
        for x in i.paths:
            for c in x:
                string+=c
                string+='->'
            string = string[:len(string)-2]
            print('{0}, {1}, {2}'.format(i.nameOfOwner, 'has path', string))
            string = ''
        print(i.maxLen)

def origin():

    projectNameAndPath = {}

    projectsWithFeature = []

    dependencyMap = defaultdict(list)

    mapArtifactId = defaultdict(list)

    mapSpecificVersion = []

    updatingList = []

    baseProjects = []

    allTrees = []

    commitMessageList = []

    searchForProjectPath(projectNameAndPath)

    mapProjects(projectNameAndPath, dependencyMap, mapArtifactId, mapSpecificVersion)

    getBaseProjects(projectNameAndPath, baseProjects, dependencyMap)

    createProjectListWithFeatures(dependencyMap, mapArtifactId, projectsWithFeature, mapSpecificVersion, projectNameAndPath)

    createTree(projectNameAndPath, baseProjects, projectsWithFeature, allTrees)

    addBaseProjectUpdatingList(baseProjects, updatingList)

    getReverseOfTree(allTrees)

    deleteBaseNodesOnTree(allTrees, baseProjects)

    findLeafAndUpdateProjects(allTrees[0], updatingList, allTrees)

    tryGitPython(projectsWithFeature)

    updatingProjects(updatingList, projectNameAndPath, projectsWithFeature, commitMessageList)




def tryGitPython(projectsWithFeature):
    os.chdir("D:\projects\maven-dependency-updater")
    repo = Repo("D:\projects\maven-dependency-updater")
    repo.git.checkout('master')
    repo.git.add('main.py','pom.xml')
    repo.git.commit('-m','Testing')
    repo.git.pull('yerel-yedek','master')
    namespaces = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
    tree = ET.parse('pom.xml')
    roots = tree.getroot()
    for d in roots.findall("xmlns:artifactId", namespaces=namespaces):
        for project in projectsWithFeature:
            if project.projectName == d.text:
                a = roots.find("xmlns:version",namespaces=namespaces).text
                if isClientVersionCompatible(a[:len(a)-9],project.projectVersion):
                    project.projectVersion =a[:len(a)-9]




def main():
    origin()

if __name__ == "__main__": main()


