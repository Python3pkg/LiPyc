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
from threading import Event, Lock

from lipyc.fs.abstract_scheduler import AbstractScheduler 
from lipyc.fs.inner_scheduler import InnerScheduler 
from lipyc.fs.config import *

counter = 0
delay_snapshot = 100#nombre d'operations entre deux snapshots

class Scheduler:
    ##
    # lib_name - uniq id, used lib name for instance
    def __init__(self, lib_name, path):
        self.Exit = Event()
        self.lib_name = lib_name
        self.id_client = random()
        self.path = path
        self.abstractScheduler = AbstractScheduler(lib_name, self.id_client, default_replicat, path)
        self.innerScheduler = InnerScheduler(lib_name, self.id_client, self.abstractScheduler, self.Exit, path)
        #self.files = set()
        
        self.innerScheduler.start()

    def __del__(self):
        self.Exit.set()

    ##fp devient la propirété de scheduler
    def add_file(self, fp, md5=None, size=None ): #current location of the file, fp location or file descriptor
        if fp:
            if isinstance(fp, str):
                fp = open(fp, "rb")
            else:
                fp.seek(0)
            
        if not md5:
            md5 = lipyc.crypto.md5( fp )
            
        if not size or size <= 0:
            size = os.fstat(fp.fileno()).st_size
        
        self.innerScheduler.add( ('added', fp, md5, size)  )
            
        return md5
            
    def __contains__(self, md5):
        return md5 in self.abstractScheduler.files
     
    def duplicate_file(self, md5):
        self.innerScheduler.add( ('added', None, md5, 0) )

        return md5
        
    def remove_file(self, md5):
        if not md5 in self.abstractScheduler.files:
            raise Exception("Scheduler, file can not be deleted because it does not exist")
                    
        self.innerScheduler.add( ('removed', None, md5, None) )

    def get_file(self, md5):
        if md5 not in self.abstractScheduler.files:
           return None

        return self.abstractScheduler.get_file(md5)
    ##
    #
    # @param struct set of pgs
    def update_structure(self, replicat, struct):
        self.innerScheduler.add( ('struct', replicat, struct) )
        
    def load(self):
        self.abstractScheduler.load()
        
        #for key in self.abstractScheduler.files:
            #self.files.add(key)
        
    def store(self):
        self.Exit.set()
        while self.innerScheduler.is_alive():
            sleep(1)

        self.abstractScheduler.store()
        
    def info(self):        
        return self.abstractScheduler.info()
    
    
    #peut être qu'on peut réutiliser les transactions
    def quick_restore(self):#be carfull must be used at the start of the application
        if self.innerScheduler.is_alive():
            self.Exit.set()
            
        while self.innerScheduler.is_alive():
            sleep(1)
            
        self.innerScheduler.reset_storage()
        self.Exit.clear()
        
        self.innerScheduler = InnerScheduler(self.lib_name, self.id_client, self.abstractScheduler, self.Exit, self.path)
        self.innerScheduler.quick_restore()
        self.loading = False
        self.innerScheduler.start()
        #self.abstractScheduler.quick_restore()
        
        #self.files.clear()
        #for key in self.abstractScheduler.files:
            #self.files.add(key)

    def reset_storage(self):        
        if self.innerScheduler.is_alive():
            self.Exit.set()
            
        while self.innerScheduler.is_alive():
            sleep(1)
            
        self.innerScheduler.reset_storage()
        self.abstractScheduler.reset_storage()
