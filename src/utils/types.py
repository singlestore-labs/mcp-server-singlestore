class Tool:
    def __init__(self, name, description, func):
        self.name = name
        self.description = description
        self.func = func

class Resource:
    def __init__(self, name, description, func, uri):
        self.name = name
        self.description = description
        self.func = func
        self.uri = uri

