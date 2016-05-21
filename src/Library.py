from tkinter import messagebox
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

from lipyc.utility import io_protect, check_ext
from lipyc.Album import Album
from lipyc.File import File


class Library:
    def __init__(self, location, load=True):
        if load and not os.path.isdir( location ):
            raise Exception("Cannot load, invalid location")
        
        self.files = {} # ordered by hash
        self.albums = set() #orderder by id
        self.inner_albums = {}#years, month 
        
        self.io_lock = threading.Lock()
        
        self.location = location
        if self.location :
            self.load()
    
    def __str__(self):
        return "Library\nFiles : %d\nAlbums : %d\ninner_albums : %d\n" % (len(self.files), len(self.albums), len(self.inner_albums))
        
    def __deepcopy__(self, memo):
        new = Library(self.location, False)
        
        new.files = copy.deepcopy( self.files)
        new.albums = copy.deepcopy( self.albums)
        new.inner_albums = copy.deepcopy( self.inner_albums)
        
        return new
        
    def __exit__(self):
        self.store()
        
    @io_protect()
    def load(self):
        files = ["files.lib", "albums.lib", "inner_albums.lib"]
        for filename in files:
            if not os.path.isfile( os.path.join(self.location, filename) ) :
                return False

        with open( os.path.join(self.location, "files.lib"), 'rb') as f:
            self.files = pickle.load(f)
            
        with open( os.path.join(self.location, "albums.lib"), 'rb') as f:
            self.albums = pickle.load(f)
            
        with open( os.path.join(self.location, "inner_albums.lib"), 'rb') as f:
            self.inner_albums = pickle.load(f)
       
    @io_protect()
    def store(self):
        with open( os.path.join(self.location, "files.lib"), 'wb') as f:
            pickle.dump(self.files, f, pickle.HIGHEST_PROTOCOL)
            
        with open( os.path.join(self.location, "albums.lib"), 'wb') as f:
            pickle.dump(self.albums, f, pickle.HIGHEST_PROTOCOL)
            
        with open( os.path.join(self.location, "inner_albums.lib"), 'wb') as f:
            pickle.dump(self.inner_albums, f, pickle.HIGHEST_PROTOCOL)
     
    @io_protect()
    def add_file(self, _file):
        if _file.md5 in self.files :
            if _file.metadata == self.files[_file.md5].metadata :
                return True
            else:
                logging.debug("Metadatas don't match %s %s" %(self.files[self._file].location, _file.location))
                return False # or run manual check
        
        _file.store(self.location)
        year, month =  (_file.metadata.year, _file.metadata.month)
        
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
        self.inner_albums[ (year, month) ].add_file( _file, self.location)
        self.files[_file.md5]= _file
        
    def add_directory(self, location):
        th = threading.Thread(None, self.inner_add_directory, None, (location,))
        th.start()
        
        return th
        
    #don io_protect this
    def inner_add_directory(self, location):
        for path, dirs, files in os.walk(location):
            for filename in files:
                if check_ext(filename) :                    
                    tmp = File(filename, os.path.join(path, filename))                    
                    self.add_file( File(filename, os.path.join(path, filename)) )
            
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
            album.decr_all()
            if album.cover :
                os.remove( album.cover )
                


 
