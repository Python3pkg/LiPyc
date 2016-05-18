from lipyc.panels.Panel import Panel

class LeftPanel(Panel):
    def __init__(self, app, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        
    def set_pagination(self, objs):
        pass
        
    def set_display(self, obj):
        pass
