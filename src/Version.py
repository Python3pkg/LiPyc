class Versionned:
    def __init__(self):
        self._version = 0
    
    def __setattr__(self, name, value):
        if "_version" in self.__dict__:
            super().__setattr__("_version", self._version+1) 
        else:
            super().__setattr__("_version", 0) 

        super().__setattr__(name, value)
    
    def version(self):
        return self._version
