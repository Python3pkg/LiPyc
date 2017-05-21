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
import time

from math import ceil
from enum import Enum

from lipyc.utility import io_protect, check_ext, make_thumbnail
from lipyc.Version import Versionned
from lipyc.config import *

from ctypes import c_int
from lipyc.autologin import *

from copy import deepcopy
#from lipyc.scheduler import scheduler


class FileMetadata:
    def __init__(self, parent = None):
        self.parent = parent
       
        self.datetime  = None
        self.year = None
        self.month = None
        self.width, self.height = 0, 0
        self.size = 0
        
    def sql(self):
        return (self.parent.id, self.datetime, self.year, self.month,
        self.width, self.height, self.size) 
    
    def __deepcopy__(self, memo, new_parent=None):
        new = FileMetadata(new_parent if new_parent else self.parent)    
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
                for tag, value in list(info.items()):
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
        
        self.datetime = time.mktime(self.datetime)
    
    def __eq__(self, m2):
        return self.datetime == m2.datetime

class File(Versionned):
    def __init__(self, id, scheduler, md5, filename):
        super().__init__()
        
        self.id = id
        self.scheduler = scheduler
        
        self.md5 = md5
        self.filename = filename
        self.metadata = FileMetadata(self)      
        self.thumbnail = None
    
    def __deepcopy__(self, memo):
        new = File(self.id, self.scheduler, self.md5, self.filename)
        
        new.metadata = deepcopy(self.metadata)
        new.thumbnail = deepcopy(self.thumbnail)
        return new
        
    def sql(self):
        return (self.id, self.md5, self.filename, self.thumbnail) 
    
    def extract(self, location): #called only the first time
        with open(location, "rb") as f:
            self.md5 = hashlib.md5(f.read()).hexdigest()
            self.metadata.extract(location)
    
    def create_thumbnails(self, location):
        if check_ext(self.filename, img_exts):
            self.thumbnail = make_thumbnail(self.scheduler, location )
        else:
            self.thumbnail = self.scheduler.add_file( location_file_default )#md5 and size can be compute before...once for the whole application
                   
    def store(self, location): 
        self.scheduler.add_file( location, self.md5, self.metadata.size )
      
    def duplicate(self):
        self.scheduler.duplicate_file(self.md5)
        if self.thumbnail:
            self.scheduler.duplicate_file(self.thumbnail)
      
    def export_to(self, path):
        location = os.path.join(path, self.filename)
        
        if not os.path.isfile(location):
            with self.scheduler.get_file(self.md5) as fp1:
                with open(location, 'wb') as fp2:
                    return shutil.copyfileobj( fp1, fp2)
            
    def remove(self):   
        if self.thumbnail:
            self.scheduler.remove_file( self.thumbnail )
        
        if self.md5:
            self.scheduler.remove_file( self.md5 )

