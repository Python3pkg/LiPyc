import json
import os
from time import time

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
        return '%s-%s-%d' % (self.id_client, self.id_lib, self.time)
    
    def __hash__(self):
        return hash((self.id_client, self.id_lib, self.time))
    
    def __eq__(self, other):
        return (self.id_client == other.id_client 
        and self.id_lib == other.id_lib and self.time == other.time)
    
    def __le__(self, other):
        return self.time < other.time or (self.time==other.time and self.id_client < other.id_client)
    
    def __len__(self):
        return len(self.data)
   
    def load(self, path):
        with open(os.join.path(path, self.name()), 'w') as fp:
            self.data = json.load(fp)
        
    def save(self, path):
        with open(os.join.path(path, self.name()), 'w') as fp:
            json.dump(self.data, fp)
