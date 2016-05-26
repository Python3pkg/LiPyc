from PIL import Image
from PIL.ExifTags import TAGS


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

from lipyc.utility import io_protect, check_ext, make_thumbnail
from lipyc.Version import Versionned
from lipyc.config import *

from ctypes import c_int
from lipyc.autologin import *
from lipyc.scheduler import scheduler


class FileMetadata:
    def __init__(self, parent = None):
        self.parent = parent
       
        self.datetime  = None
        self.year = None
        self.month = None
        self.width, self.height = 0, 0
        self.size = 0
    
    def __deepcopy__(self, memo, new_parent=None):
        new = FileMetadata( new_parent if new_parent else self.parent)    
        new.datetime  = copy.deepcopy( self.datetime )
        new.year = copy.deepcopy( self.year )
        new.month = copy.deepcopy( self.month )
        new.width, new.height = copy.deepcopy( self.width ), copy.deepcopy( self.height )
        
        return new
        
    def extract(self, location):   
        if check_ext(self.parent.filename, img_exts):
            image = Image.open(location)
            self.width, self.height = image.size
        else:
            image = None
             
        self.extract_datetime(image, location)
        self.size = os.path.getsize( location )
        
    def extract_datetime(self, image, location):
        self.datetime  = None
        if image:
            info = image._getexif()
            if info :
                for tag, value in info.items():
                    decoded = TAGS.get(tag, tag)
                    if decoded == 'DateTime' or decoded == 'DateTimeOriginal':
                        self.datetime  = time.strptime( value, "%Y:%m:%d %H:%M:%S")
            else:
                logging.debug("info empty for %s   %s" % (location, self.parent.filename))
    
        if not self.datetime :
            nbs = os.path.getmtime(location)
            self.datetime  = time.gmtime(nbs)
        
        self.year    = time.strftime("%Y", self.datetime)
        self.month   = time.strftime("%m", self.datetime)
    
    def __eq__(self, m2):
        return self.datetime == m2.datetime

class File(Versionned):
    def __init__(self, md5, filename):
        super().__init__()
        
        self.filename = filename
        self.md5 = md5
        self.metadata = FileMetadata(self)      
        self.thumbnail = None
                     
        self.io_lock = threading.Lock() #pour gérer les export concurrant à une suppression si wait vérouiller on ne peut pas supprimer

    def __deepcopy__(self, memo):
        new = File(self.md5, self.filename)
        new.thumbnail = self.thumbnail
        new.metadata = self.metadata.__deepcopy__(None, new)
        new.io_lock = self.io_lock
        
        return new
    
    def __getstate__(self):
        tmp = copy.copy( self.__dict__ )
        del tmp["io_lock"]
        return tmp
    
    def __setstate__(self, state):
        self.__dict__ = state
        self.io_lock = threading.Lock()
    
    def extract(self, location): #called only the first time
        with open(location, "rb") as f:
            self.md5 = hashlib.md5(f.read()).hexdigest()
            self.metadata.extract(location)
    
    def create_thumbnails(self, location):
        if check_ext(self.filename, img_exts):
            self.thumbnail = make_thumbnail( location )
        else:
            self.thumbnail = scheduler.add_file( "file_default.png" )#md5 and size can be compute before...once for the whole application
                   
    def store(self, location): 
        scheduler.add_file( location, self.md5, self.metadata.size )
      
    def export_to(self, location):
        raise Exception("export_to not rewritte yet")
        #if not os.path.isfile(location):
            #flag = shutil.copy2( self.location, location) == location
         
    @io_protect() #la seule à devoir être proteger, du fait de la construction de l'application
    def remove(self):   
        if self.thumbnail:
            scheduler.remove_file( self.thumbnail )
        
        if self.md5:
            scheduler.remove_file( self.md5 )

