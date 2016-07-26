import json
import os
from time import time
from functools import total_ordering

@total_ordering
class Transaction:
    def __init__(self, id_client, id_lib):
        self.time = time()
        self.id_client = id_client
        self.id_lib = id_lib
    
        self.data = []
        
    def add(self, row):
        self.data.append(row)
        
    def id(self):
        return self.name()
        
    def name(self):
        return '%s-%s-%d' % (self.id_lib, self.id_client, self.time)
    
    def __hash__(self):
        return hash((self.id_client, self.id_lib, self.time))
    
    def __eq__(self, other):
        return (self.id_client == other.id_client 
        and self.id_lib == other.id_lib and self.time == other.time)
    
    def __le__(self, other):
        return self.time < other.time or (self.time==other.time and self.id_client < other.id_client)
    
    def __len__(self):
        return len(self.data)
   
    def load(self, path):#todo for ftp
        self.data, data = [], []
        
        pl = path.split('-')
        self.lib_name = pl[0]
        self.id_client = pl[1]
        self.time = int(pl[2])
        
        with open(os.path.join(path), 'r') as fp:
            data = json.load(fp)
        
        for tmp in data:
            t,row = tmp[0], tmp[1:]
            if t == 'added':
                self.data.append( tuple([t, None] + row) )
            else:
                self.data.append(tmp)
        
    def save(self, path):#todo for ftp
        if not self.data:
            return False
            
        data = []
        for tmp in self.data:
            t,row = tmp[0], tmp[1:]
            if t == 'added':
                data.append( [t] + list(row[1:]) )
            else:
                data.append(tmp)
                
        with open(os.path.join(path, self.name()), 'w') as fp:
            json.dump(data, fp)
        
        return True
