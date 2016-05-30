import numpy as np
import json
from copy import copy
from lipyc.crypto import AESCipher
import itertools, functools
import os
import hashlib
import lipyc.crypto 
import logging
import shutil
import tempfile
import pickle
import threading
import collections
import sys

from random import random

def wrand(seed, value):
    a, b = 6364136223846793005, 1
    
    return a * ((a * seed + b) ^ value ) + b; 

def make_path(path, md5):
    return os.path.join( path, "%s" % md5) 

def counter(cls):
    id_name = "_%s__id" % cls.__name__
    if id_name in cls.__dict__:
        return cls
    
    cls.__id = 0

    def _warpe(method):
        def _warper(self, *args, **kwargs):
            cls.__id +=1
            self._id = cls.__id

            method(self, *args, **kwargs)
        return _warper
            
    setattr(cls, "__init__", _warpe(cls.__init__))

    if hasattr(cls, "__copy__"):
        setattr(cls, "__copy__", _warpe(cls.__copy__))
    else:
        def _copy(self):
            newone = type(self)()
            nid = newone._id
            newone.__dict__.update(self.__dict__)
            newone._id = nid
            return newone
        setattr(cls, "__copy__", lambda self:_copy(self))
    setattr(cls, "__get_id__", lambda _=None: cls._id)

    return cls

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

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
    
    def add_(self, obj):#construction n^2....
        if not self.children:
            self.children.add( obj )
            return 
        min_obj = min( self.children, key=lambda x:x.free_capacity )
        
        
        if obj.free_capacity < min_obj.free_capacity :
            self.children.add( obj )
            return
        
        r = int(obj.free_capacity / min_obj.free_capacity)
        self._min_obj = obj

        for k in range(min(r, max_ratio)):
            tmp = copy(obj)
            tmp.max_capacity /= r
            tmp.free_capacity /= r
            
            self.children.add( tmp )
                
    def __str__(self, ident=' '):
        buff="%sContainer %d: %s, %d/%d : %f\n" % (ident, self._id,self.name, self.free_capacity, self.max_capacity, float(self.free_capacity)/(float(self.max_capacity)))
        for child in self.children:
            buff+=child.__str__(ident*2)
        return buff
    
@counter        
class Bucket: #décrit un dossier ex: photo, gdrive, dropbox
    def make(name, json_bucket, aeskey):
        return Bucket(path=json_bucket["path"], 
            max_capacity=json_bucket["max_capacity"],
            speed=json_bucket["speed"],
            name=name,
            crypt=json_bucket["crypt"],
            aeskey=json_bucket["aeskey"] if "aeskey" in json_bucket else aeskey)
            
    def __init__(self, max_capacity=0, path="", speed=1.0, name="", crypt=False, aeskey=""):
        self.name = name
        self.crypt = crypt
        self.aeskey = aeskey
        
        self.free_capacity = max_capacity
        self.max_capacity = max_capacity
        self.speed = speed
        self.path = path
            
    def write(self, md5, size, fp):
        self.free_capacity -= size
        if self.crypt :
            self.free_capacity -= 2*lipyc.crypto.BS
        assert(self.free_capacity >= 0)
        
        last = fp.tell()
        fp.seek(0)

        if self.crypt :
            cipher = AESCipher(self.aeskey)
            with open(make_path(self.path, md5), "wb") as fp2:
                cipher.encrypt_file( fp, fp2)
        else:
            with open(make_path(self.path, md5), "wb") as fp2:
                shutil.copyfileobj(fp, fp2)
                
        fp.seek(last)
    
    def remove(self, md5, size):
        self.free_capacity += size        
        assert(self.free_capacity <= self.max_capacity)
        os.remove( make_path(self.path, md5) )
    def __str__(self, ident=' '):
        buff="%sBucket %d: %s, %d/%d : %f\n" % (ident, self._id, self.name, self.free_capacity, self.max_capacity, float(self.free_capacity)/(float(self.max_capacity)))

        return buff

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
            key = lambda obj:wrand( obj._id, key)) 
            
    def place(self, key, size):
        self.free_capacity -= size 

        bucket = min( self.children, 
            key = lambda obj:wrand( obj._id, key))
        if bucket.crypt :
            self.free_capacity -= 2*lipyc.crypto.BS
        if bucket.free_capacity < size:
            logging.error("Cannot save file, no more space available in %s" % self)
            raise Exception("No More Space")
            #en fait il faudrait passer le bucket en passive mod et trouver un algo qui cmarche pour le placement
            self.rebalance() 
                
        return bucket
    
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
    
    def place(self, key, size):
        self.free_capacity -= size 
        
        child = min( self.children, 
            key = lambda obj:wrand( obj._id, key))
           
           
        bucket = child.place( key, size )
        if bucket.crypt :
            self.free_capacity -= 2*lipyc.crypto.BS
                
        if child.free_capacity < size:
            logging.error("Cannot save file, no more space available in %s" % self)
            raise Exception("No More Space")
            #en fait il faudrait passer le bucket en passive mod et trouver un algo qui cmarche pour le placement
            self.rebalance() 
                
        return bucket
    
    def access(self, key):
        child = min( self.children, 
            key = lambda obj:wrand( obj._id, key))
        
        return child.access( key )
        
    def buckets(self):
        return itertools.chain( map( Pool.children, self.children ))
        
class Scheduler(Container):
    def __init__(self, replicat=2):
        super().__init__()
        self.pgs = self.children
        self.replicat = replicat
        
        #self.degraded = False #not enought place to assure replication, container and bucket too, not use
        self.passive = True #no data yet
        self.files = {} #ensemble des fichiers gérés : md5 => size, number(nombre de creation)
        
        self.db_lock = threading.Lock()
        self.locks = {}#md5=>num_read,write_lock
        
        
    
    def place_(self, key):
        pgs = sorted(self.pgs, key = lambda obj:wrand( obj._id, key))
        return [pg for _,pg in zip( range(self.replicat), pgs) ]
        
    def place(self,  key, size=0): 
        return map( lambda pg: pg.place(key, size), self.place_(key))

    def access(self, key):
        pgs = sorted(self.pgs, key = lambda obj:wrand( obj._id, key))
        buckets = [ pg.access( key ) for _,pg in zip( range(self.replicat), pgs) ]
        tmp_buckets = list( filter( lambda bucket: not bucket.crypt, buckets) )
        
        if tmp_buckets:
            buckets = tmp_buckets
        
        sum_speed = float( functools.reduce(lambda acc,b: acc + b.speed, buckets, 0) )
        rand_number = random()
        current_speed = 0
        for bucket in buckets:
            current_speed += float(bucket.speed)/sum_speed
            if rand_number < current_speed:
                return bucket
        
        return buckets[-1] 
    
        
    def add_file(self, fp, md5=None, size=None ): #current location of the file, fp location or file descriptor
        self.passive = False
        if isinstance(fp, str):
            fp = open(fp, "rb")
        else:
            fp.seek(0)
            
        if not md5:
            md5 = lipyc.crypto.md5( fp )
            
        if not size or size <= 0:
            size = os.fstat(fp.fileno()).st_size
            
        if md5 in self.files: #deduplication ici
            self.files[md5][1]+=1
            return md5
            
        with self.db_lock: #thread protection
            if not md5 in self.locks:
                self.locks[md5]= {"read":0, "write":threading.Lock()}
            condition = threading.Condition(self.locks[md5]["write"])
        
        with condition:
            condition.wait_for(lambda _=None: self.locks[md5]["read"]==0 )    
            
            key = int(md5, 16)
            assert(len(list(self.place(key, 0))) == self.replicat)
            for bucket in self.place(key, size):
                bucket.write( md5, size, fp )
            
            if md5 not in self.files:
                self.files[md5] = [size,1]
            else:
                self.files[md5][1] += 1
            for pg in self.pgs:
                print(pg)
                
            #raise Exception("")
            return md5
            
    def __contains__(self, md5):
        with self.db_lock:
            if not md5 in self.locks:
                self.locks[md5]= {"read":0, "write":threading.Lock()}
                
        with self.locks[md5]["write"]:
            return md5 in self.files
     
    def duplicate_file(self, md5):
        with self.db_lock:
            if not md5 in self.locks:
                self.locks[md5]= {"read":0, "write":threading.Lock()}
                
        with self.locks[md5]["write"]:
            self.files[md5][1]+=1
            return md5
        
    def remove_file(self, md5):
        with self.db_lock: #thread protection
            if not md5 in self.locks:
                self.locks[md5]= {"read":0, "write":threading.Lock()}
            condition = threading.Condition(self.locks[md5]["write"])
        
        with condition:
            condition.wait_for(lambda _=None: self.locks[md5]["read"]==0 )   
        
        
            #for pg in self.pgs:
                #print(pg)
            self.passive = False
            self.files[md5][1] -= 1

            if self.files[md5][1] > 0:
                return 
            key = int(md5, 16)

            for bucket in self.place(key, -1 * self.files[md5][0]):
                bucket.remove(md5, self.files[md5][0])
                
            del self.files[md5]
            #for pg in self.pgs:
                #print(pg)

    def get_file(self, md5):
        with self.db_lock: #thread protection
            if not md5 in self.locks:
                self.locks[md5]= {"read":0, "write":threading.Lock()}
        
        with self.locks[md5]["write"]:
            self.locks[md5]["read"] += 1
            
        if md5 not in self.files:
            self.locks[md5]["read"] -= 1
            return None

        key = int(md5, 16)        
        bucket = self.access(key)
        if not bucket.crypt:
            self.locks[md5]["read"] -= 1
            return open( make_path(bucket.path, md5), "rb")
        else:
            cipher = AESCipher(bucket.aeskey)
            fp2 = tempfile.TemporaryFile(mode="r+b")
            with open(make_path(bucket.path, md5), "rb") as fp:
                cipher.decrypt_file( fp, fp2)
            self.locks[md5]["read"] -= 1
            return fp2
    
    #all method below are not thread safe
    def __str__(self):
        return str(self.pgs)  
          
    def add_pg(self, pg):
        if self.passive:
            return super().add(pg)
         
        files_to_move = {}
        for md5,size in self.files.items():
            key = int(md5, 16)
            pgs = self.place_(key)
            pgs.append( pg )
            pg_max = max(pgs, key=lambda obj:wrand( obj._id, key))
            if pg != pg_max:
                bucket = max_pg.place(key)
                
                pg.place(key).write( md5, size, make_path(bucket.path, afile) )
                bucket.remove( md5, size )
        
    def remove_pg(self, pg):
        if self.passive:
            return super().remove(pg)

        files_to_move = {}
        for md5,size in self.files:
            key = int(md5, 16)
            pgs = self.place_(key)
            if pg in pgs:
                pgs.remove(pg)
                files_to_move.add( (key, (md5, size), pgs) )
        
        self.pgs.discard(pg)
        
        for key,(md5, size),pgs in files_to_move:
            bucket = pg.place( key )
            for n_pg in filter(lambda n_pg: n_pg not in pgs, self.place_(key)):#en pratique un seul
                n_pg.place(key).write( md5, size, make_path(bucket.path, md5) )
            bucket.remove( md5, size )
        
    def parse(self):
        if not os.path.isfile("pgs.json"):
            return False
            
        with open("pgs.json", "r") as fp: #il faut preserver les ids sinon on ne retrouvera plus les fichiers
            config = json.load(fp)

            global max_ratio#a modifier
            max_ratio = config["max_ratio"]
            self.replicat = config["replicat"]
            aeskey = config["aeskey"] if "aeskey" in config else ""

            assert( len(config["pgs"]) == len(config["pgs"].keys()))

            pgs=list(config["pgs"].items())
            for name, json_pg in pgs:
                tmp = PG.make(name, json_pg, aeskey)
                self.add( tmp )
    
    def load(self):
        if os.path.isfile("scheduler.data"):
            with open( "scheduler.data", 'rb') as f:
                data = pickle.load(f)
                self.pgs.update(data["pgs"] )
                self.files.update(data["files"] )
                self.replicat = data["replicat"]
                self.passive = data["passive"]
        else:
            self.parse()
        
        if os.path.isfile("files.json"):
            with open("files.json", "r") as f :
                self.files = json.load(f)
        
    def store(self):
        with open("files.json", "w") as f :
            json.dump(self.files, f)
        
        with open("scheduler.data", 'wb') as f:
            data={
                'pgs':self.pgs,
                'files':self.files,
                'replicat':self.replicat,
                'passive':self.passive
            }
            
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
    
    def info(self):        
        measurement_unit = 1024*1024#calcul exacte par raport à l'unité choisie(heuristic....)

        
        mc = int(sum( [int(pg.max_capacity / measurement_unit) for pg in self.pgs])/self.replicat) 
        fc = int(sum( [int(pg.free_capacity / measurement_unit) for pg in self.pgs])/self.replicat)
        
        mc *= measurement_unit
        fc *= measurement_unit

        report = {
            "usage": int(100 * float(mc-fc) / float(mc)) if mc > 0 else 0,
            "capacity": sizeof_fmt(mc-fc),
            "true_capacity": sizeof_fmt(sum( [ size for size,_ in self.files.values() ] )),
            "max_capacity": sizeof_fmt(mc),
            "free_capacity": sizeof_fmt(fc),
            "replicat": self.replicat,
            "passive":self.passive
        }
        return report
    
    def buckets(self):
        return itertools.chain( map( Pool.children, self.pgs ))

scheduler=Scheduler()  #variable globale pour l'application jusqu'à ce que je troouve une meilleur idée (FUSE : Linux, Mac)
scheduler.load()
#print("===================================================")
#test_files = [location_file_default, location_album_default, "pgs.json"]
#for loc in test_files:
    #m = scheduler.add_file(loc)
    #tmp = scheduler.get_file( m )
    #assert( lipyc.crypto.md5(tmp) == lipyc.crypto.md5(loc))
    #tmp.close()
    #scheduler.remove_file(m)

#raise Exception("End")
