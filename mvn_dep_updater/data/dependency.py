class Dependency:
    def __init__(self, id, var_name, version, isParent = False):
        self.id = id
        self.version = version
        self.var_name = var_name
        self.dependencies = {}
        self.isParent = isParent


    def add_dependency(self, dependency):
        self.dependencies[dependency.id] = dependency

    def get_dependencies(self):
        return self.dependencies