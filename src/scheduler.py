import numpy as np
import json
from copy import copy
from lipyc.crypto import AESCipher
import itertools
import os

def wrand(seed, value):
    #speed, the placement groupe, pool id etc
    a, b = 6364136223846793005, 1
    
    return a * ((a * seed + b) ^ value ) + b; 

def make_path(path, afile):
    return os.path.join( "path", "%s_%s" % (afile.md5[:16],afile.filename)) 

def counter(cls):
    id_name = "_%s__id" % cls.__name__
    if id_name in cls.__dict__:
        return cls
    
    setattr(cls, "__id", 0)
    setattr(cls, id_name, 0)

    def _warpe(method):
        def _warper(self, *args, **kwargs):
            cls.__id +=1
            self.__id = cls.__id

            method(self, *args, **kwargs)
        return _warper
            
    setattr(cls, "__init__", _warpe(cls.__init__))

    if hasattr(cls, "__copy__"):
        setattr(cls, "__copy__", _warpe(cls.__copy__))
    else:
        pass
        #def _copy(self):
            #cls.__id +=1
            #self.__id = cls.__id
            #super().__copy__()
        setattr(cls, "__copy__", _warpe(lambda self:super.__copy__(self)))
    setattr(cls, "__get_id__", lambda _=None: cls.__id)

    return cls

#speed use only to select : read replicat
#nom => identifiant unique pour l'utilisateur(au sein d'un mêm parent)
max_ratio = 100 #on ne peut multiplier la proba que par 5 au plus
class Container:
    def __init__(self, name=""):
        self.name = name
        self.free_capacity = 0
        self.max_capacity = 0
        self.speed = 1.
        
        self.children = set()
        
        self._min_obj = None
        
    def add(self, obj, disjoint=False):
        self.max_capacity += obj.max_capacity
        self.free_capacity += obj.free_capacity
        self.speed += obj.speed if disjoint else 0
        
        self.add_(obj)
        assert(self.free_capacity >= 0)
        
                    
    def remove(self, obj, disjoint=False):
        self.max_capacity -= obj.max_capacity
        self.free_capacity += (obj.max_capacity - obj.free_capacity)
        self.speed -= obj.speed if disjoint else 0
        
        self.children.discard(obj)
        assert(self.free_capacity <= self.max_capacity)
    
    def add_(self, obj):
        if not self._min_obj:
            self._min_obj = obj
            return
            
        if self._min_obj.free_capacity <= obj.free_capacity:
            return
        
        r = int(obj.free_capacity / self._min_obj.free_capacity)
        self._min_obj = obj
        
        for k in range(min(r, max_ratio)):
            tmp = copy(obj)
            tmp.max_capacity /= r
            tmp.free_capacity /= r
            
            self.children.add( tmp )
                
@counter        
class Bucket(Container): #décrit un dossier ex: photo, gdrive, dropbox
    def make(name, json_bucket, aeskey):
        return Bucket(path=json_bucket["path"], 
            max_capacity=json_bucket["max_capacity"],
            speed=json_bucket["speed"],
            name=name,
            crypt=json_bucket["crypt"],
            aeskey=json_bucket["aeskey"] if "aeskey" in json_bucket else aeskey)
            
    def __init__(self, max_capacity, path, speed=1.0, name="", crypt=False, aeskey=""):
        self.name = name
        self.crypt = False
        
        self.free_capacity = max_capacity
        self.max_capacity = max_capacity
        self.speed = speed
        self.path = path
        
        #self.files = {}#file to location

    def add_file(self, afile):
        self.free_capacity -= afile.metadata.size       
        assert(self.free_capacity >= 0)
        #self.files.add(afile)
        
    def remove_file(self, afile):
        self.free_capacity += afile.metadata.size        
        assert(self.free_capacity <= self.max_capacity)
        #self.files.discard(afile)
    
    def access(self, afile):
        return self.files[afile]
        
    def write(self, afile, location):
        if bucket.crypt :
            cipher = AESCipher(self.aeskey)
            encrypt_file( open(location, "rb"), open(make_path(self.path, afile), "wb"))
        else:
            shutil.copy2(location, make_path(self.path, afile))
    
    def remove(self, afile):
        os.remove( make_path(self.path, afile) )
    
@counter
class Pool(Container):  #on décrit un disque par exemple avec pool
    def make(name, json_pool, aeskey):#config json to pool
        pool = Pool(name)
        aeskey = json_pool["aeskey"] if "aeskey" in json_pool else ""
        
        for name, json_pool in json_pool["buckets"].items():
            pool.add( Bucket.make(name, json_pool, aeskey) )
        
        return pool
    
    def access(self, key):
        return min( self.children, 
            key = lambda obj:wrand( obj.__id, key)) 
            
    def place(self, key):
        child = min( self.children, 
            key = lambda obj:wrand( obj.__id, key))
                
        if child.free_capacity < afile.metadata.size:
            logging.error("Cannot save file, no more space available in %s" % self)
            raise Exception("No More Space")
            #en fait il faudrait passer le bucket en passive mod et trouver un algo qui cmarche pour le placement
            self.rebalance() 
                
        return child
    
    def buckets(self):
        return itertools.chain( self.children )
@counter
class PG(Container):
    def make(name, json_pg, aeskey):#config json to pg
        pg = PG(name)
        aeskey = json_pg["aeskey"] if "aeskey" in json_pg else ""
        for name, json_pool in json_pg["pools"].items():
            pg.add( Pool.make(name, json_pool, aeskey) )
        
        return pg
    
    def place(self, key):
        child = min( self.children, 
            key = lambda obj:wrand( obj.__id, key))
                
        if child.free_capacity < afile.metadata.size:
            logging.error("Cannot save file, no more space available in %s" % self)
            raise Exception("No More Space")
            #en fait il faudrait passer le bucket en passive mod et trouver un algo qui cmarche pour le placement
            self.rebalance() 
                
        return child.place( key )
    
    def access(self, key):
        child = min( self.children, 
            key = lambda obj:wrand( obj.__id, key))
        
        return child.access( key )
        
        
    def buckets(self):
        return itertools.chain( map( Pool.children, self.children ))
        
class Scheduler(Container):
    def __init__(self, replicat=2):
        super().__init__()
        self.pgs = self.children
        self.replicat = replicat
        
        self.degraded = False #not enought place to assure replication, container and bucket too, not use
        self.passive = True #no data yet
        self.files = set() #ensemble des fichiers gérés
        
    def place_(self, key):
        pgs = sorted(self.pgs, key = lambda obj:wrand( obj.__id, key))
        return [pg for _,pg in zip( range(self.replicat), pgs) ]
        
    def place(self,  key):     
        return map( lambda pg: pg.place(key), self.place_(key))                      
        
    def access(self, key):
        pgs = sorted(self.pgs, key = lambda obj:wrand( obj.__id, key))
                
        buckets = [ pg.acces( key ) for _,pg in zip( range(self.replicat), pgs) ]
        bucket = max( filter( lambda bucket: not bucket.crypt, buckets), key=lambda bucket:bucket.speed)
        
        if not bucket:
            bucket = max( buckets, key=lambda bucket:bucket.speed)
        return bucket
        
    def add_file(self, afile, location): #current location of the file
        self.passive = False
        key = int(afile.md5, 16)
        
        for bucket in self.place(key):
            bucket.write( afile )
        
        self.files.add(afile)
        
    def remove_file(self, afile):
        self.passive = False
        key = int(afile.md5, 16)
        
        for bucket in self.place(key):
            bucket.remove(afile)
            
        self.files.discard(afile)

    def get_file(self, afile):
        key = int(afile.md5, 16)        
        bucket = self.access(key)
        
        return open( make_path(bucket.path, afile), "r")
    
    def add_pg(self, pg):
        if self.passive:
            return super().add(pg)
         
        files_to_move = {}
        for afile in self.files:
            key = int(afile.md5, 16)
            pgs = self.place_(key)
            pgs.append( pg )
            pg_max = max(pgs, key=lambda obj:wrand( obj.__id, key))
            if pg != pg_max:
                bucket = max_pg.place(key)
                
                pg.place(key).write( afile, make_path(bucket.path, afile) )
                bucket.remove( afile )
        
    def remove_pg(self, pg):
        if self.passive:
            return super().remove(pg)

        files_to_move = {}
        for afile in self.files:
            key = int(afile.md5, 16)
            pgs = self.place_(key)
            if pg in pgs:
                pgs.remove(pg)
                files_to_move.add( (key, afile, pgs) )
        
        self.pgs.discard(pg)
        
        for key,afile,pgs in files_to_move:
            bucket = pg.place( key )
            for n_pg in filter(lambda n_pg: n_pg not in pgs, self.place_(key)):#en pratique un seul
                n_pg.place(key).write( afile, make_path(bucket.path, afile) )
            bucket.remove( afile )
        
    def load(self, location):
        with open(location, "r") as f:
            config = json.load(open("pgs.json"))
            
            global max_ratio#a modifier
            max_ratio = config["max_ratio"]
            self.replicat = config["replicat"]
            aeskey = config["aeskey"] if "aeskey" in config else ""
            
            for name, json_pg in config["pgs"].items():
                self.add( PG.make(name, json_pg, aeskey) )
    
    def buckets(self):
        return itertools.chain( map( Pool.children, self.pgs ))

s = Scheduler()  
s.load("pgs.json")          
pg = PG()
p = Pool()
b1 = Bucket( 1024, "" )
b2 = Bucket( 2048, "" )

p.add( b1 )
p.add( b2 )

pg.add(p)
s.add(pg)            
