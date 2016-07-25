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

from lipyc.fs.utility import *
from lipyc.fs.config import *

class Container:
    def __init__(self, name="", max_capacity=0, speed=1.):
        self._name = name
        self.free_capacity = max_capacity
        self.max_capacity = max_capacity
        self.speed = speed
        
        self.children = set()
        
        self._min_obj = None
        self.lock = Lock()

        self._id = generate_id(name)

    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, _name):
        self._id = generate_id(_name)
        self._name = _name
  
    def add(self, obj, disjoint=False):
        self.max_capacity += obj.max_capacity
        self.free_capacity += obj.free_capacity
        self.speed += obj.speed if disjoint else 0
        
        self._add(obj)
        assert(self.free_capacity >= 0)
      
    def remove(self, obj, disjoint=False):
        self.max_capacity -= obj.max_capacity
        self.free_capacity -= obj.free_capacity
        self.speed -= obj.speed if disjoint else 0
        
        self.children.discard(obj)
        assert(self.free_capacity <= self.max_capacity)
   
    def _add(self, obj):#construction n^2....
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
        
    def update_stats(self):
        self.free_capacity = 0
        for child in self.children:
            self.free_capacity += child.free_capacity
          
          
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
          
          
    def __eq__(self, other):
        return self.name == other.name
      
    def __hash__(self):
        return hash(self.name)

    def __str__(self, ident=' '):
        buff="%sContainer %d: %s, %d/%d : %f\n" % (ident, self._id, self.name, self.free_capacity, self.max_capacity, float(self.free_capacity)/(float(self.max_capacity+1)))
        for child in self.children:
            buff+=child.__str__(ident*2)
        return buff
    
    def __getstate__(self):
        return {
            '_id':self._id,
            'name':self.name,
            'free_capacity':self.free_capacity,
            'max_capacity':self.max_capacity,
            'speed':self.speed,
            'children':self.children,
            '_min_obj':self._min_obj,
        }
    
    def clear(self):
        self.free_capacity = self.max_capacity
        
        for x in self.children :
            x.clear()
        
    def __setstate__(self, state):
        self._id = state['_id']
        self.name = state['name']
        self.free_capacity = state['free_capacity']
        self.max_capacity = state['max_capacity']
        self.speed = state['speed']
        self.children = state['children']
        self._min_obj = state['_min_obj']
        self.lock=Lock()
          
    def buckets(self):
        return itertools.chain( *list(map( lambda x:x.buckets(), self.children )))
