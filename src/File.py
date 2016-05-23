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


class FileMetadata(WorkflowStep):
    def __init__(self, parent = None):
        self.parent = parent
       
        self.datetime  = None
        self.thumbnail  = None
        self.year = None
        self.month = None
        self.width, self.height = 0, 0
        self.size = 0
    
    def __deepcopy__(self, memo, new_parent=None):
        new = FileMetadata( new_parent if new_parent else self.parent)    
        new.datetime  = copy.deepcopy( self.datetime )
        new.thumbnail  = copy.deepcopy( self.thumbnail )
        new.year = copy.deepcopy( self.year )
        new.month = copy.deepcopy( self.month )
        new.width, new.height = copy.deepcopy( self.width ), copy.deepcopy( self.height )
        
        return new
        
    def extract(self):   
        if check_ext(self.parent.filename, img_exts):
            image = Image.open(self.parent.location)
            self.width, self.height = image.size
        else:
            image = None
             
        self.extract_datetime(image)
        self.extract_thumbnail()
        self.size = os.path.getsize( self.parent.location )
        
    def extract_datetime(self, image):
        self.datetime  = None
        if image:
            info = image._getexif()
            if info :
                for tag, value in info.items():
                    decoded = TAGS.get(tag, tag)
                    if decoded == 'DateTime' or decoded == 'DateTimeOriginal':
                        self.datetime  = time.strptime( value, "%Y:%m:%d %H:%M:%S")
            else:
                logging.debug("info empty for %s   %s" % (self.parent.location, self.parent.filename))
    
        if not self.datetime :
            nbs = os.path.getmtime(self.parent.location)
            self.datetime  = time.gmtime(nbs)
        
        self.year    = time.strftime("%Y", self.datetime)
        self.month   = time.strftime("%m", self.datetime)
    
    def extract_thumbnail(self, path=""):
        name, ext = os.path.splitext(self.parent.filename)
        self.thumbnail = os.path.join( path, "." + name + ".thumbnail")
    
    def __eq__(self, m2):
        return self.datetime == m2.datetime

class File(Versionned):
    def __init__(self, filename=None, location=None, extracted = False):
        super().__init__()
        
        self.filename = filename
        self.location = location
        self.md5 = None
        self.metadata = FileMetadata(self)      
        self.extracted = extracted  
        
        if location and filename and not self.extracted:
            self.extract()
        
        self.garbage_number = c_int(0) #if 0 then data suppressed
        
        self.io_lock = threading.Lock() #pour gérer les export concurrant à une suppression si wait vérouiller on ne peut pas supprimer

    def __deepcopy__(self, memo):
        new = File(self.filename, self.location, self.extracted)
        new.md5 = self.md5
        new.metadata = self.metadata.__deepcopy__(None, new)
        new.garbage_number = self.garbage_number #danger
        #logging.warning("Warning", "Using file deepcopy, you must ensure that garbage collector is still right")
        new.extracted = self.extracted #sort du garbage collector si on le copie
        new.io_lock = self.io_lock
        
        return new
    
    def __getstate__(self):
        tmp = copy.copy( self.__dict__ )
        del tmp["io_lock"]
        return tmp
    
    def __setstate__(self, state):
        self.__dict__ = state
        self.io_lock = threading.Lock()
    
    def extract(self):
        self.extracted = True
        with open(self.location, "rb") as f:
            self.md5 = hashlib.md5(f.read()).hexdigest()
            self.metadata.extract()
    
    def create_thumbnails(self):
        if check_ext(self.filename, img_exts):
            make_thumbnail( self.location, self.metadata.thumbnail)
        else:
            shutil.copy2("file_default.png", self.metadata.thumbnail)
       
    def store(self, path): 
        dst = os.path.join(path, self.metadata.year, self.metadata.month)
        if not os.path.isdir(dst):
            os.makedirs( dst )
        dst =  os.path.join(dst, self.filename)
        
        flag = True
        if not os.path.isfile(dst):
            flag = shutil.copy2( self.location, dst) == dst
            
        self.location = dst
        self.metadata.extract_thumbnail(path)
        self.create_thumbnails()
        return flag
      
    def export_to(self, location):
        if not os.path.isfile(location):
            flag = shutil.copy2( self.location, location) == location
         
    @io_protect() #la seule à devoir être proteger, du fait de la construction de l'application
    def remove(self):      
        if os.path.isfile(self.location):
            os.remove( self.location )
            
        if os.path.isfile(self.metadata.thumbnail):
            os.remove( self.metadata.thumbnail )

