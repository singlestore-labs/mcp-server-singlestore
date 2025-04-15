class Tool:
    def __init__(self, name, description, func, inputSchema):
        self.name = name
        self.description = description
        self.func = func
        self.inputSchema = inputSchema