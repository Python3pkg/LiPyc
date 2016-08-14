## @file 
# @author Laurent Prosperi
# @date June 2016
# @brief Not thread-safe( not the purpose)

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
from threading import Lock, Condition
import collections
import sys
from time import time, sleep
from random import random

from lipyc.fs.container import Container
from lipyc.fs.pg import PG
from lipyc.fs.config import *
from lipyc.fs.utility import *

class AbstractScheduler(Container):
    ##
    # lib_name - uniq id, used lib name for instance
    def __init__(self, lib_name, id_client, replicat, path):
        super().__init__()
        self.lib_name = lib_name
        self.id_client  = id_client
        
        self.pgs = self.children
        self.replicat = replicat
        
        self.path = path
        
        self.files = {} #ensemble des fichiers gérés : md5 => size, number(nombre de creation)
            
        #self.history = []#must be locked by_dblock
        self.previous_snapshot = 0

    #def snapshot(self): #should be called in db_lock mod
        #if delay_snapshot <= len(self.history) and self.previous_snapshot<time():
            #t= time()
            #with open("snapshot-%d.json" % t, "w") as f :
                #json.dump(self.history, f)
                #self.history.clear()
            #self.previous_snapshot = t
        
    def prune(self):
        for pg in self.pgs :
            if not pg.children:
                self.remove(pg)

    def _place(self, key):
        pgs = sorted(self.pgs, key = lambda obj:wrand( obj._id, key))
        return [pg for _,pg in zip( range(self.replicat), pgs) ]
        
    def place(self,  key, size=0): 
        return map( lambda pg: pg.place(key, size), self._place(key))

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
        
    def add_file(self, fp, md5, size ): #current location of the file, fp location or file descriptor
        #self.snapshot()
        if md5 in self.files: #deduplication ici
            self.files[md5][1]+=1
            #self.history.append( ('update',md5, self.files[md5][1]) )
            return md5
        #else:
            #self.history.append( ('added', md5, size) )
                

        key = int(md5, 16)
        assert(len(list(self.place(key, 0))) == self.replicat)
        for bucket in self.place(key, size):
            bucket.write( md5, size, fp )
        global counter
        counter+=1

        self.files[md5] = [size,1]
        #self.history.append( ('added', md5, size) )
        if fp:
            fp.close()
        
        return md5
            
    def __contains__(self, md5):
        return md5 in self.files
        
    def remove_file(self, md5):
        if md5 not in self.files:
            return
            
        self.files[md5][1] -= 1
        if self.files[md5][1] > 0:
            return 
        key = int(md5, 16)

        for bucket in self.place(key, -1 * self.files[md5][0]):
            bucket.remove(md5, self.files[md5][0])
            
        del self.files[md5]
        
        #self.history.append( ('removed', md5, None) )

    def get_file(self, md5):
        if md5 not in self.files:
            return None

        key = int(md5, 16)        
        bucket = self.access(key)
        return bucket.get_file(md5)
       
    
    ##
    # @param struct set of pgs
    def update_structure(self, replicat, struct):
        new_scheduler = AbstractScheduler( self.lib_name, self.id_client, replicat, self.path )
        for pg in struct:
            new_scheduler.add(pg)
            
        for md5,(size,counter) in self.files.items():
            key = int(md5, 16)

            new_buckets = set(map( lambda pg: pg.place(key, size), new_scheduler._place(key)))
            pre_buckets = set(map( lambda pg: pg.place(key, 0), self._place(key)))

            ins_buckets = new_buckets.difference( pre_buckets )
            del_buckets = pre_buckets.difference( new_buckets )

            with self.get_file(md5) as fp:
                for bucket in ins_buckets:
                    bucket.write(md5, size, fp)
            
            for bucket in del_buckets:
                bucket.remove(md5, 0)
                
        for pg in new_scheduler.pgs:
            pg.update_stats()  

        self.replicat = new_scheduler.replicat
        self.children.clear()
        self.children.update( new_scheduler.children)
        
        assert( self.replicat == new_scheduler.replicat)
        assert( self.replicat == replicat)
    #all method below are not thread safe
    def __str__(self):
        return str(self.pgs)  
        
    def location_of(self, filename):
        return os.path.join(self.path, filename)
        
    def isfile(self, filename):
        return os.path.isfile( self.location_of(filename) )
    
    def parse(self):
        if not self.isfile("pgs.json"):
            shutil.copy2(location_pgs_default, self.location_of('pgs.json'))
            
        with open(self.location_of("pgs.json"), "r") as fp: #il faut preserver les ids sinon on ne retrouvera plus les fichiers
            config = json.load(fp)

            global max_ratio#a modifier
            max_ratio = config["max_ratio"]
            self.replicat = config["replicat"]
            aeskey = config["aeskey"] if "aeskey" in config else ""

            assert( len(config["pgs"]) == len(config["pgs"].keys()))

            pgs=list(config["pgs"].items())
            for name, json_pg in pgs:
                tmp = PG.make(self.lib_name, name, json_pg, aeskey)
                self.add( tmp )
    
    def pgs2json(self):
        data = {}
        
        global max_ratio
        data['max_ratio'] = max_ratio
        data['replicat'] = self.replicat
        data['aeskey'] = ''
        data['pgs'] = {}
        
        for pg in self.pgs: 
            tmp = {'aeskey':'', 'pools':{}, 
                'max_capacity':pg.max_capacity, 'free_capacity':pg.free_capacity}         
            for pool in pg.children:
                tmp2 = {'buckets':{}, 'aeskey':'',
                    'max_capacity':pool.max_capacity, 
                    'free_capacity':pool.free_capacity}
                for bucket in pool.children:
                    tmp3 = {
                        'path':bucket.path,
                        'max_capacity':bucket.max_capacity,
                        'free_capacity':bucket.free_capacity,
                        'speed':bucket.speed,
                        'crypt':bucket.crypt,
                        'aeskey':bucket.aeskey,
                        'login':bucket.login,
                        'pwd':bucket.pwd
                    }
                    tmp2['buckets'][bucket.name.split('|')[-1]] = tmp3
                tmp['pools'][pool.name.split('|')[-1]] = tmp2
            data['pgs'][pg.name] = tmp
        
        return data
        
    def load(self):
        self.parse()

        if self.isfile("files.json"):
            with open(self.location_of("files.json"), "r") as f :
                self.files = json.load(f)
        
    def store(self):
        with open(self.location_of("files.json"), "w") as f :
            json.dump(self.files, f)
        
        with open(self.location_of("pgs.json"), "w") as f :
            json.dump(self.pgs2json(), f)
             
        #with open(self.location_of("scheduler.data"), 'wb') as f:
            #data={
                #'pgs':self.pgs,
                #'files':self.files,
                #'replicat':self.replicat
            #}
            
            #pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
        
        #self.snapshot()
        #global delay_snapshot
        #delay_snapshot = 1
        #self.snapshot()
    
    def reset_storage(self):
        if self.isfile('files.json'):
            os.remove(self.location_of('files.json'))
        if self.isfile('pgs.json'):
            os.remove(self.location_of('pgs.json'))
        
        for b in self.buckets():
            b.reset_storage()
    
    def info(self):        
        measurement_unit = 8*1024*1024#calcul exacte par raport à l'unité choisie(heuristic....)

        
        mc = int(sum( [int(pg.max_capacity / measurement_unit) for pg in self.pgs])/self.replicat) 
        fc = int(sum( [int(pg.free_capacity / measurement_unit) for pg in self.pgs])/self.replicat)
        
        mc *= measurement_unit
        fc *= measurement_unit

        report = {
            "usage": int(100 * float(mc-fc) / float(mc)) if mc > 0 else 0,
            "capacity": sizeof_fmt((mc-fc)*self.replicat),
            "true_capacity": sizeof_fmt(self.replicat * sum( [ size for size,_ in self.files.values() ] )),
            "max_capacity": sizeof_fmt(mc),
            "free_capacity": sizeof_fmt(fc),
            "replicat": self.replicat
        }
        return report
    
    def buckets(self):
        return itertools.chain( *list(map( lambda x:x.buckets(), self.pgs )) )

    #def quick_restore(self):#be carfull must be used at the start of the application
        #self.clear()
        ##self.history.clear()
        #begin = time() #faut supprimer tout les trucs créée entre temps
        
        #locations= []
        #for path, dirs, files in os.walk('.'):
            #for filename in files:
                #location = os.path.join(path, filename)
                
                #if filename[:9] == 'snapshot-' and int(filename[9:-5])<begin :  
                    #locations.append(location)
        
        #for location in sorted(locations):
            #with open(location, "r") as f :
                #history = json.load(f)
                
            #for t, md5, v1 in history:
                #if t == 'added':
                    #self.add_file( None, md5, v1)
                #elif t == 'update' :
                    #for k in range(v1-self.files[md5][1]):
                        #self.duplicate_file(md5)
                #elif t == 'removed':
                    #self.remove_file(md5)
        
        ##self.history.clear()
        #for path, dirs, files in os.walk('.'):
            #for filename in files:
                #location = os.path.join(path, filename)
                #if filename[:9] == 'snapshot-' and int(filename[9:-5])>=begin :
                    #os.remove( location )
        
        #print("End restore!!")

    def clear(self):
        super().clear()
        self.files.clear()
