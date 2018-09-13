class Dependency:
    def __init__(self, dependecy_id, dependecy_version, isParent = False):
        self.dependecy_id = dependecy_id
        self.dependecy_version = dependecy_version
        self.dependencies = {}
        self.isParent = isParent


    def add_dependency(self, dependency):
        self.dependencies[dependency.dependecy_id] = dependency

    def get_dependencies(self):
        return self.dependencies