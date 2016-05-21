from tkinter import * 
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox

#sudo apt-get install libtiff5-dev libjpeg8-dev zlib1g-dev \
    #libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python-tk

from PIL import Image
from PIL import ImageTk# https://pillow.readthedocs.io/en/3.2.x/   libjpeg-dev sudo pip3 install pillow  sudo apt-get install libjpeg8-dev python3-pil.imagetk
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

from timeit import default_timer


from lipyc.panels.MenuBar import TopMenu
from lipyc.panels.LeftPanel import LeftPanel
from lipyc.panels.RightPanel import RightPanel
from lipyc.panels.MainPanel import MainPanel

from lipyc.Library import Library
from lipyc.Album import Album
from lipyc.File import File
from lipyc.config import *


#class Certificat(Enum):
    #add_album = 0

class Application(Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
                
        self.library = None
        
        self.parents_album = [] #if we are in subalbums for insertion supression etc
        
        self.selected = set()
        self.selected_mod = False

        self.current = 0 #page number   
        self.action = Action.pagination_albums

        self.io_threads=[]

        self.topMenu = TopMenu(self, self)
        self.config(menu=self.topMenu)
        
        self.mainPanel = MainPanel(self, self)
        self.mainPanel.grid(row=0, column=1)
        
        self.leftPanel = LeftPanel(self, self)
        self.leftPanel.grid(row=0, column=0)
        
        self.rightPanel = RightPanel(self, self)
        self.rightPanel.grid(row=0, column=2)
        
        self.register_events()
        self.register_ticks()
        self.protocol("WM_DELETE_WINDOW", self.clean)
        
        self.load()

        
    def load(self):
        files = ["general.data"]
        for filename in files:
            if not os.path.isfile( filename ) :
                return False
        
        with open( "general.data", 'rb') as f:
            general = pickle.load(f)

            if general :
                if general["library_location"] and os.path.isdir( general["library_location"] ):
                    self.library = Library(general["library_location"])
                    self.rightPanel.actionPanel.set()
                    
                self.parents_album = general["parents_album"]
                self.current = general["current"]
                self.action = general["action"]
        
        self.refresh()
        
    def store(self):
        general={
            'library_location' : self.library.location if self.library else None,
            'parents_album' : self.parents_album,
            'current' : self.current,
            'action' : self.action,
        }
        with open("general.data", 'wb') as f:
            pickle.dump(general, f, pickle.HIGHEST_PROTOCOL)
      
    def clean(self):
        self.save()
        for th in self.io_threads:
            if th.is_alive():
                th.join()
        self.destroy()
#### Async IO
    def save(self):
        self.io_threads = [ th for th in self.io_threads if th.is_alive ]                
        self.save_library()
        self.store()
    
    def save_library(self):
        if self.library :
            t = threading.Thread(None, (lambda lib : lib.store()), None, (copy.deepcopy(self.library),) )#snapshot
            t.start()
            self.io_threads.append(t)

    def register_events(self):
        def _keypress_event(event):
            if event.keycode == 37 or event.keycode == 105: #ctrl
                self.selected_mod = True
        
        def _keyrelease_event(event): 
            if event.keycode == 37 or event.keycode == 105: #ctrl
                self.selected_mod = False
            if event.keycode == 119:
                self.remove( self.selected )

        def escape(e):
            if self.parents_album :
                self.back()
        self.bind("<Escape>", escape)
        self.bind("<KeyPress>", _keypress_event)
        self.bind("<KeyRelease>", _keyrelease_event)
        
    def register_ticks(self):
        def _save():
            self.after(300000, _save)#ms, each 5 minutes
            self.save()
        
        def _refresh():
            self.refresh()
            self.after(3000, _refresh) #ms, each 5 minutes
        
        self.after(300000, _save)
        self.after(3000, _refresh)
        self.after(3000, _refresh)
       
    def select(self, obj):
        if not self.selected_mod :
            self.selected.clear()

        self.selected.add(obj)
        self.refresh()
    


#### Begin Views
    def display_albums(self, albums):
        self.action = Action.pagination_albums

        self.mainPanel.set_pagination(albums)
        self.leftPanel.set_pagination(albums)
        self.rightPanel.set_pagination(self.selected)
        
        self.mainPanel.show()
        self.leftPanel.show()
        self.rightPanel.show()
        
    def display_files(self, files):
        self.action = Action.pagination_files
        
        self.mainPanel.set_pagination(files)
        self.leftPanel.set_pagination(files)
        self.rightPanel.set_pagination(self.selected)
        
        self.mainPanel.show()
        self.leftPanel.show()
        self.rightPanel.show()
        
    def display_file(self, _file):
        self.action = Action.display_file

        self.mainPanel.set_display(_file)
        self.leftPanel.set_display(_file)
        self.rightPanel.set_display(_file)
        
        self.mainPanel.show()
        self.leftPanel.show()
        self.rightPanel.show()
#### End Views               

 
    #def make_add_album(self, frame):
        #clean_frame( frame )
        #frame.pack(side=LEFT)
        
        #name = StringVar() 
        #name.set("Album name")
        #name_entry = Entry(frame, textvariable=name, width=10)
        #name_entry.pack(side=LEFT)
        
        #button = Button(frame, text="Add")
        #button.bind("<Button-1>", lambda event: self.add_album(name.get(), frame))
        #button.pack(side=LEFT)
        
        #frame.pack()
        
    #def make_rename_album(self, handler, frame):
        #clean_frame( frame )
        #frame.pack(side=TOP)
        
        #name = StringVar() 
        #name.set(handler.album.name)
        #name_entry = Entry(frame, textvariable=name, width=15)
        #name_entry.pack(side=LEFT)
        
        #button = Button(frame, text="Rename")
        #button.bind("<Button-1>", lambda event: self.rename_album(name.get()))
        #button.pack(side=LEFT)
  
#### End Make
    
     
## Begin Event Handling
#### Begin TopPanel
    def back(self):
        self.parents_album.pop()
        self.current = 0
        self.action = Action.pagination
        self.refresh()
          
    def add_album(self, name, frame):
        if not name :
            messagebox.showerror("Error", "Invalid name for album name")

        album = Album( name )
        if self.parents_album :
            self.parents_album[-1].add_subalbum( album )
        else:
            self.library.add_album( album )
               
        #clean_frame(frame)
        #b_add_album = Button(frame, text="Add album", command= lambda _=None : self.make_add_album(f_add_album) )
        #b_add_album.pack(side=LEFT)
        #frame.pack(side=LEFT)
               
        self.action = Action.pagination_albums
        self.rightPanel.actionPanel.set()
        self.refresh()

    def show_files(self, current=0):
        self.current = current
        self.action = Action.pagination_files

        if self.parents_album :
            self.display_files( self.parents_album[-1].files)
        else:
            self.display_files([])
                
    def show_albums(self, current=0):
        self.current = current
        self.action = Action.pagination_albums
        
        if self.parents_album :
            self.display_albums( self.parents_album[-1].subalbums)
        else:
            self.display_albums(self.library.albums)

#### Begin TopPanel



#### Begin Menu
    def set_library_location(self, location=None):
        self.save_library()
        
        if not location:
            location = filedialog.askdirectory()
        
        if not location:
            return False
            
        if not os.path.isdir( location ):
            messagebox.showerror("Error", "Library location : invalid")
        
        self.library = Library( location )
        
        self.parents_album.clear()
        self.selected.clear()
        
        self.rightPanel.actionPanel.set()
        
        self.action = Action.pagination
        self.refresh()

    def import_directory(self):
        location = filedialog.askdirectory()

        if not self.library:
            messagebox.showerror("Error", "Library location : not defined")
            return False
            
        if not location :
            return False
        
        if not os.path.isdir( location ):
            messagebox.showerror("Error", "Source location : not defined")
            return False
        self.io_threads.append( self.library.add_directory( location ) )
          
    def _export_to(files, albums):
        for _file in files:
            _file.export_to(location)
            _file.io_lock.release()
            
        for album in albums:
            album.export_to(location)
             
        files = copy.deepcopy( [handler._file for handler in self.selected_files]  )
        albums = copy.deepcopy( [handler.album for handler in self.selected_albums])
        
        for _file in files:
            _file.io_lock.acquire()

        th = threading.Thread(None, _export_to, None, ( files, albums))
        th.start()
        self.io_threads.append(th)
        
    def export_to(self):
        location = filedialog.askdirectory()
        if not location :
            return False
            
        if not os.path.isdir( location ):
            messagebox.showerror("Error", "No target specified")
            return False
        
        if not self.selected_albums and not self.selected_files:
            messagebox.showerror("Error", "Nothing to export")
            return False
    
    
#### End Menu
     
#### Begin RightPanel

###### Begin ActionPanel
    # Warning : 
    #       Never done deepcopy on a file, and use it as usual,
    #    such a deecopy will disable the garbage collector for  the new object
    
    def add_to(self,  parent_album):
        for obj in self.selected:
            if isinstance(obj, Album):
                parent_album.add_subalbum( obj )
            else:
                parent_album.add_file( obj, self.library.location )
                
    def copy_to(self, parent_album):
        for obj in self.selected:
            if isinstance(obj, Album):
                parent_album.add_subalbum( copy.deepcopy( obj ) )
            else:
                parent_album.add_file( obj, self.library.location )
        
    def move_to(self, parent_album):        
        for obj in list(self.selected):
            if isinstance(obj, Album):
                parent_album.add_subalbum( obj  )
                self.remove_album( obj )
            else:
                parent_album.add_file( obj, self.library.location )
                self.remove_file( obj )
        
###### End ActionPanel

#### End RightPanel

#### Begin BottomPanel
    def next_page(self):
        self.current += 1
        self.refresh()
        
    def previous_page(self):
        self.current -= 1
        self.refresh()
      
#### End BottomPanel
## End Event Handling
    
    def rename_album(self, name):
        if not name :
            messagebox.showerror("Error", "Invalid name for album name")
            
        (list(self.selected_albums)[0].album).rename( name )
        
        self.rightPanel.actionPanel.set()
        self.refresh()
        
    def _refresh(self):
        if not self.library:
            return None
        if self.action == Action.pagination:
            if self.parents_album and self.parents_album[-1].files:
                self.action = Action.pagination_files
            else:
                self.action = Action.pagination_albums
            
        if self.action == Action.pagination_files:
            self.show_files(self.current)
        elif self.action == Action.pagination_albums:
            self.show_albums(self.current)
        elif self.action == Action.display_file:
            pass
        
    def refresh(self):
        s = default_timer()
        self._refresh()
        #print("Refresh duration %f",  default_timer()-s)
   
    def remove_file(self, _file, refresh=False):#surtout pas de thread io
        self.parents_album[-1].remove_file( _file, self.library.files )
        
        self.selected.discard(_file)
    
        if refresh:
            self.refresh()
            
    def remove_album(self, album, refresh=False):#surtout pas de thread io
        album.remove_all(self.library.files)

        if self.parents_album:
            self.parents_album[-1].remove_subalbum( album )
        self.library.remove_album( album )
        
        self.selected.discard( album )
           
        self.rightPanel.actionPanel.set()
        if refresh:
            self.refresh()
    
    def remove(self, objs):
        for obj in list(objs):
            if isinstance(obj, Album):
                self.remove_album(obj)
            else:
                self.remove_file(obj)
                
        self.refresh()
