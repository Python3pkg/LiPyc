from lipyc.panels.Panel import Panel
from lipyc.panels.RightPanel import InfoPanel
from lipyc.scheduler import scheduler

class LeftPanel(Panel):
    def __init__(self, app, master, *args, **kwargs):
        super().__init__(master, width=150, *args, **kwargs)
        
        self.app = app
        
        self.infoPanel = InfoPanel(self, 10, 10)
                
        self.infoPanel.grid(row=0, column=0)
        self.infoPanel.show()
        

        self.set_display = self.set
        self.set_pagination = self.set
       
        self.scheduler_info = None
    
    def set(self, objs):#display only the status of the scheduler
        report = scheduler.info()
        if self.scheduler_info == report:
            return
        self.scheduler_info = report
        
        labels_texts=[
        "Space usage(heuristic) : %d%%" % report["usage"],
        "Free space(heuristic) : %s" % report["free_capacity"],
        "Used space : %s" % report["capacity"],
        "Used space(real) : %s" % report["true_capacity"],
        "Replicat(s) : %d" % report["replicat"],        
        ]

        buttons_texts=[]
        callbacks = []
        
        self.infoPanel.set_labels(labels_texts)
        self.infoPanel.set_buttons(buttons_texts, callbacks)
        self.infoPanel.show()

