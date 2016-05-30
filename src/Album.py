from PIL import Image

import os.path,os
import pickle
import hashlib
import time
import random
import logging
import copy
import threading
import itertools
from math import ceil
from enum import Enum

from lipyc.utility import recursion_protect
from lipyc.Version import Versionned
from lipyc.config import *
from lipyc.utility import check_ext, make_thumbnail
from lipyc.scheduler import scheduler

from tkinter import messagebox

class Album(Versionned): #subalbums not fully implemented
    def __init__(self, name=None, datetime=None):
        super().__init__()
        
        self.name = name
        self.datetime = datetime if datetime else time.gmtime()
        self.subalbums = set()
        
        self.thumbnail = scheduler.add_file( **thumbnails["album"] )
        self.files = set() #order by id
        self.inner_keys = [] #use for inner albums
        
    def rename(self, name):
        self.name = name
        
    def add_file(self, _file):
        if self.thumbnail == None and  _file.thumbnail :
            self.thumbnail = scheduler.duplicate_file( _file.thumbnail )

        self.files.add(_file)
        
    def remove_file(self, _file):
        self.files.discard(_file)       
        _file.remove()
    
    @recursion_protect()
    def remove_all(self):
        for album in list(self.subalbums):
            album.remove_all()
        self.subalbums.clear()
        
        for _file in list(self.files):
            self.remove_file(_file)
        self.files.clear()
        
    def add_subalbum(self, album):
        self.subalbums.add( album )
    
    def remove_subalbum(self, album):
        if album in self.subalbums:           
            if album.thumbnail :
                scheduler.remove_file( album.thumbnail )
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
    
    def set_thumbnail(self, location):
        if self.thumbnail :
            scheduler.remove_file(self.thumbnail)
        
        if not isinstance(location, str) or check_ext(location, img_exts): #fichier ouvert
            self.thumbnail = make_thumbnail( location )
        else:
            self.thumbnail = scheduler.add_file(location_album_default) #size and md5  ought to be combute once for all
    
    def deep_files(self):
        tmp = itertools.chain.from_iterable(map(Album.deep_files, self.subalbums))
        return itertools.chain( self.files, tmp)
    
    
    @recursion_protect(0)
    def __len__(self): #number of file in dir and subdir
        return len(self.files) + sum( [len(a) for a in self.subalbums ] )
   
