class Project:
    def __init__(self, project_id, project_version, path, dependencies):
        self.project_id = project_id
        self.project_version = project_version
        self.dependencies = dependencies
        self.path = path
        self.level = 0

    def is_base_project(self):
        return len(self.dependencies.keys()) == 0
