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
from lipyc.fs.scheduler import Scheduler
from lipyc.db import DBFactory
import lipyc.crypto 
from lipyc.config import *

class Library(WorkflowStep):
    ## 
    # @param name - uniq id
    def __init__(self, name, location, load=True): #location where metada are stored
        if load and not os.path.isdir( location ):
            raise Exception("Cannot load, invalid location")
        
        self.albums = set() #orderder by id
        self.inner_albums = {}#years, month 
        
        self.io_lock = threading.Lock()
        
        self.name = name
        self.location = location
        self.scheduler=Scheduler(name, self.location)
        
        self.ressource_counter = 0
        
    def __str__(self):
        return ""
        
    def __deepcopy__(self, memo):
        new = Library(self.name, self.location, False)
        
        new.albums = copy.deepcopy( self.albums)
        new.inner_albums = copy.deepcopy( self.inner_albums)
        new.scheduler = self.scheduler # cannot be copied but it's thread-safe
        return new
        
        
    def __exit__(self):
        self.store()
        
    @io_protect()
    def load(self):
        self.scheduler.load()

        db = DBFactory(self.location)
        files = db.build_files(self.scheduler)
        albums = db.build_albums(self.scheduler, files)
        
        self.albums = db.build_first_layer_albums(albums)
        self.inner_albums = db.build_inner_albums(albums)
        
        self.ressource_counter = db.init_counter()
        db.close()

        return (files, albums)
        #with open( os.path.join(self.location, "albums.lib"), 'rb') as f:
            #self.albums = pickle.load(f)
            
        #with open( os.path.join(self.location, "inner_albums.lib"), 'rb') as f:
            #self.inner_albums = pickle.load(f)

                
    @io_protect()
    def store(self):
        files = set()
        for alb in itertools.chain( *list([x.all_albums() for x in self.albums]) ):
            files.update( alb.files )
            
        db = DBFactory(self.location)
        db.save_files(files)
        db.save_albums(itertools.chain( *list([x.all_albums() for x in self.albums]) ))
        db.save_first_layer_albums(self.albums)
        db.save_inner_albums(self.inner_albums)
        db.close()

        #with open( os.path.join(self.location, "albums.lib"), 'wb') as f:
            #pickle.dump(self.albums, f, pickle.HIGHEST_PROTOCOL)
            
        #with open( os.path.join(self.location, "inner_albums.lib"), 'wb') as f:
            #pickle.dump(self.inner_albums, f, pickle.HIGHEST_PROTOCOL)
        
        self.scheduler.store()
     
    @io_protect()
    def add_file(self, afile, file_location):
        if afile.md5 in self.scheduler : #dedup des objs python
            return True
        
        self.ressource_counter +=1
        afile.extract(file_location)
        afile.create_thumbnails(file_location) 
        afile.store(file_location)
        
        year, month =  (afile.metadata.year, afile.metadata.month)

        if (year, month) not in self.inner_albums:
            if year not in self.inner_albums:
                y_album = Album(self.ressource_counter, self.scheduler, year )
                self.ressource_counter+=1
                
                y_album.inner_keys = [year]
                self.inner_albums[ year ] = y_album
                self.albums.add( y_album )
            else:
                y_album = self.inner_albums[ year ]
            
            
            m_album = Album(self.ressource_counter, self.scheduler, month )
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
                    self.ressource_counter+=1
                    
                    self.add_file( File(self.ressource_counter, self.scheduler, 
                    lipyc.crypto.md5( file_location ), filename), file_location)
            
    @io_protect()
    def add_album(self, album):
        self.albums.add( album )
        
    @io_protect()
    def remove_album(self, album):
        db = DBFactory(self.location)

        if len( album.inner_keys ) == 2 :
            db.delete_inner_album(album.inner_keys[0], album.inner_keys[1])
            del self.inner_albums[ (album.inner_keys[0], album.inner_keys[1]) ]
        elif len( album.inner_keys ) == 1:
            db.delete_inner_album(album.inner_keys[0])
            del self.inner_albums[ album.inner_keys[0]]

        if album in self.albums:
            self.albums.discard( album )
            db.delete_first_layer_album( album )
        
        if album.thumbnail :
            self.scheduler.remove_file( album.thumbnail )
        
        db.delete_album(album)
        self._remove_files(album.all_files(), db)
        album.remove_all()
        
    def _remove_files(self, files, db):
        db.delete_files(files)
        for _file in files:
            _file.remove()
    @io_protect()
    def remove_files(self, files):  
        self._remove_files(files, DBFactory(self.location) )
        
                
    def deep_files(self):
        return itertools.chain.from_iterable(list(map(Album.deep_files, self.albums)))

 
    def reset_storage(self):
        if os.path.exists(os.path.join(self.location, 'metadata.db')):
            os.remove( os.path.join(self.location, 'metadata.db') )
        self.scheduler.reset_storage()

    def copy_file_to(self, afile, parent):
        afile.duplicate()
        parent.add_file( afile )
    
    def copy_album_to(self, album, parent):
        album.duplicate()
        
        self.ressource_counter+=1
        parent.add_subalbum(album.clone(self.ressource_counter))
    
    def add_file_to(self, *args):
        self.copy_file_to(*args)
        
    def add_album_to(self, album, parent):
        parent.add_subalbum(album.pseudo_clone())
