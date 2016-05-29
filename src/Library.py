from tkinter import messagebox
from PIL.ExifTags import TAGS


import os.path, os
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

from lipyc.utility import io_protect, check_ext
from lipyc.Album import Album
from lipyc.File import File
from lipyc.autologin import *
from lipyc.scheduler import scheduler
import lipyc.crypto 

class Library(WorkflowStep):
    def __init__(self, location, load=True): #location where metada are stored
        if load and not os.path.isdir( location ):
            raise Exception("Cannot load, invalid location")
        
        
        self.albums = set() #orderder by id
        self.inner_albums = {}#years, month 
        
        self.io_lock = threading.Lock()
        
        self.location = location
        self.load()
    
    def __str__(self):
        return ""
        
    def __deepcopy__(self, memo):
        new = Library(self.location, False)
        
        new.albums = copy.deepcopy( self.albums)
        new.inner_albums = copy.deepcopy( self.inner_albums)
        
        return new
        
    def __exit__(self):
        self.store()
        
    @io_protect()
    def load(self):
        files = ["albums.lib", "inner_albums.lib"]
        for filename in files:
            if not os.path.isfile( os.path.join(self.location, filename) ) :
                return False
            
        with open( os.path.join(self.location, "albums.lib"), 'rb') as f:
            self.albums = pickle.load(f)
            
        with open( os.path.join(self.location, "inner_albums.lib"), 'rb') as f:
            self.inner_albums = pickle.load(f)
       
    @io_protect()
    def store(self):
        with open( os.path.join(self.location, "albums.lib"), 'wb') as f:
            pickle.dump(self.albums, f, pickle.HIGHEST_PROTOCOL)
            
        with open( os.path.join(self.location, "inner_albums.lib"), 'wb') as f:
            pickle.dump(self.inner_albums, f, pickle.HIGHEST_PROTOCOL)
     
    @io_protect()
    def add_file(self, afile, file_location):
        if afile.md5 in scheduler : #dedup des objs python
            return True
        
        afile.extract(file_location)
        afile.create_thumbnails(file_location) 
        afile.store(file_location)
        
        year, month =  (afile.metadata.year, afile.metadata.month)
        
        if (year, month) not in self.inner_albums:
            if year not in self.inner_albums:
                y_album = Album( year )
                y_album.inner_keys = [year]
                self.inner_albums[ year ] = y_album
                self.albums.add( y_album )
            else:
                y_album = self.inner_albums[ year ]
            
            m_album = Album( month )
            m_album.inner_keys = [y_album.inner_keys[0], month]
            y_album.add_subalbum( m_album )

            self.inner_albums[ (year, month) ] = m_album
        self.inner_albums[ (year, month) ].add_file( afile )
        
    def add_directory(self, location, callback):
        def inner():
            self.inner_add_directory(location)
            callback()
        th = threading.Thread(None, inner(), None)
        th.start()
        
        return th
        
    #don io_protect this
    def inner_add_directory(self, location):
        for path, dirs, files in os.walk(location):
            for filename in files:
                if check_ext(filename) :  
                    file_location = os.path.join(path, filename)
                    self.add_file( File(lipyc.crypto.md5( file_location ), filename), file_location )
            
    @io_protect()
    def add_album(self, album):
        self.albums.add( album )
        
    @io_protect()
    def remove_album(self, album):
        if len( album.inner_keys ) == 2 :
            del self.inner_albums[ (album.inner_keys[0], album.inner_keys[1]) ]
        elif len( album.inner_keys ) == 1:
            del self.inner_albums[ album.inner_keys[0]]
        
        if album in self.albums:
            self.albums.discard( album )

            if album.thumbnail :
                scheduler.remove_file( album.thumbnail )
                
    def deep_files(self):
        return itertools.chain.from_iterable(map(Album.deep_files, self.albums))

 
