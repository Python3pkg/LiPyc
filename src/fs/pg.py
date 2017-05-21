from lipyc.fs.container import Container
from lipyc.fs.pool import Pool

class PG(Container):
    def make(lib_name, name, json_pg, aeskey):#config json to pg
        pg = PG(name)
        aeskey = json_pg["aeskey"] if "aeskey" in json_pg else ""
        if 'free_capacity' in json_pg:
            pg.free_capacity = json_pg['free_capacity']
        if 'max_capacity' in json_pg:
            pg.max_capacity = json_pg['max_capacity']
            
        for _name, json_pool in list(json_pg["pools"].items()):
            pg.add( Pool.make(lib_name, name+"|"+_name, json_pool, aeskey) )
        
        return pg
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def prune(self):
        for child in self.children:
            if not child.children:
                self.remove(child)
