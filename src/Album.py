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

class Album(Versionned): #subalbums not fully implemented
    def __init__(self, name=None, datetime=None):
        super().__init__()
        
        self.name = name
        self.datetime = datetime if datetime else time.gmtime()
        self.subalbums = {}
        
        self.cover = None
        self.files = {} #order by id
        self.died = False #use if inner, because it will persiste vene affter deeleteion
        
    def alive(self):
        return not self.died
        
    def rename(self, name):
        self.name = name
        
    def add_file(self, _file):
        if self.cover == None:
            self.cover = _file
            
        _file.garbage_number += 1
        self.files[ _file ] = True
        
    def remove_file(self, _file, md5map):#va falloir enrichir le msg
        if _file.garbage_number == 1 and not messagebox.askyesno("Warning", "This is the last copy of this picture, do you really want to remove it ?"):
            return None
            
        if _file in self.files:
            del self.files[_file]
        
        _file.garbage_number -= 1
        
        if self.files and _file == self.cover:
            self.cover = random.choice(list(self.files.keys()))
        elif not self.files:
            self.cover = None
        
        if _file.garbage_number == 0:
            del md5map[_file.md5]
            _file.remove()
    
    @recursion_protect()
    def remove_all(self, md5map):
        for album in list(self.subalbums.keys()):
            album.remove_all(md5map)
            album.died = True
        self.subalbums.clear()
        
        for _file in list(self.files.keys()):
            self.remove_file(_file, md5map)
        self.files.clear()
        
    def add_subalbum(self, album):
        self.subalbums[ album ] = True
        album.incr_all()
        
    @recursion_protect()
    def incr_all(self):
        for _file in self.files:
            _files.garbage_number += 1
        
        for album in self.subalbums:
            album.incr_all()
    
    @recursion_protect()
    def decr_all(self): 
        for _file in self.files:
            _files.garbage_number -= 1
        
        for album in self.subalbums:
            album.decr_all()
            
    def remove_subalbum(self, album):
        if album in self.subalbums:
            album.died = True #only used for inner_album
            album.decr_all()
            del self.subalbums[album]
           
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
        return len(self.files) + sum( [len(a) for a in self.subalbums.keys() ] )
   
