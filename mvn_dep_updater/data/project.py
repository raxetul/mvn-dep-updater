class Project:
    def __init__(self, project_id, project_version, path, dependencies, parent_id=None):
        self.project_id = project_id
        self.project_version = project_version
        self.dependencies = dependencies
        self.path = path
        self.level = 0
        self.parent_id = parent_id
        self.child_projects = []

    def add_child_project(self,project):
        self.child_projects.append(project)

    def is_base_project(self):
        return len(self.dependencies.keys()) == 0
