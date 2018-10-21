class Project:
    def __init__(self, project_id, project_version, path, dependencies, group_id=None):
        self.project_id = project_id
        self.project_version = project_version
        self.dependencies = dependencies
        self.path = path
        self.level = 0
        self.group_id = group_id

    def is_base_project(self):
        return len(self.dependencies.keys()) == 0
