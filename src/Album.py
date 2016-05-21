import os.path
import pickle
import hashlib
import time
import shutil
import random
import logging
import copy
import threading

from math import ceil
from enum import Enum

from lipyc.utility import recursion_protect
from lipyc.Version import Versionned

from tkinter import messagebox

class Album(Versionned): #subalbums not fully implemented
    def __init__(self, name=None, datetime=None):
        super().__init__()
        
        self.name = name
        self.datetime = datetime if datetime else time.gmtime()
        self.subalbums = set()
        
        self.cover = None
        self.files = set() #order by id
        self.inner_keys = [] #use for inner albums
        
    def rename(self, name):
        self.name = name
        
    def add_file(self, _file, path):
        if self.cover == None and  _file.metadata.thumbnail :
            if not os.path.isdir( os.path.join( path, ".cover")):
                os.makedirs( os.path.join( path, ".cover") )
            self.cover = os.path.join( path, ".cover" , str(id(self)) + ".thumbnail")
            shutil.copy2(_file.metadata.thumbnail, self.cover)
            
        _file.garbage_number.value += 1
        self.files.add(_file)
        
    def remove_file(self, _file, md5map):#va falloir enrichir le msg
        if _file.garbage_number.value == 1 and not messagebox.askyesno("Warning", "This is the last copy of this picture %s, do you really want to remove it ?" % _file.filename):
            return None
            
        self.files.discard(_file)
        _file.garbage_number.value -= 1
        
        if _file.garbage_number.value == 0:
            del md5map[_file.md5]
            _file.remove()
    
    @recursion_protect()
    def remove_all(self, md5map):
        for album in list(self.subalbums):
            album.remove_all(md5map)
        self.subalbums.clear()
        
        for _file in list(self.files):
            self.remove_file(_file, md5map)
        self.files.clear()
        
    def add_subalbum(self, album):
        self.subalbums.add( album )
        album.incr_all()
        
    @recursion_protect()
    def incr_all(self):
        for _file in self.files:
            _file.garbage_number.value += 1
        
        for album in self.subalbums:
            album.incr_all()
    
    @recursion_protect()
    def decr_all(self): 
        for _file in self.files:
            _files.garbage_number.value -= 1
        
        for album in self.subalbums:
            album.decr_all()
    
    def remove_subalbum(self, album):
        if album in self.subalbums:
            album.decr_all()
            
            if album.cover :
                os.remove( album.cover)
            self.subalbums.discard( album )
    
    @recursion_protect()
    def export_to(self, path):
        location = os.path.join(path, self.name)
        if not os.path.isdir(location):
            os.makedirs( location )
            
        for _file in self.files:
            _file.export_to(location)
            
        for album in self.subalbums:
            album.export_to( location )
    
    @recursion_protect()    
    def lock_files(self):
        for _file in self.files:
            _file.io_lock.acquire()
            
        for album in self.subalbums:
            album.lock_files()   
    
    @recursion_protect(0)
    def __len__(self): #number of file in dir and subdir
        return len(self.files) + sum( [len(a) for a in self.subalbums ] )
   
