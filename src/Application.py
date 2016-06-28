from tkinter import * 
from tkinter.ttk import *
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
import random
import logging
import copy
import threading
import collections

import itertools

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
from lipyc.autologin import *
from lipyc.scheduler import scheduler
from lipyc.similarity import find_similarities

#class Certificat(Enum):
    #add_album = 0


class Application(Tk, WorkflowStep):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
                
        self.library = None
        
        self.parents_album = [] #if we are in subalbums for insertion supression etc
        
        self.selected = set()
        self.selected_mod = False

        self.current = 0 #page number   
        self.current_pagination = 0#if there is differnet paginations
        self.sortname = "name"
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

        self.last_objs  = [[]]#last_objs per pagination
        self.last_k     = -1
        
        
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
                self.last_objs = general["last_objs"]
                
        
        self.refresh()
        
    def store(self):
        general={
            'library_location' : self.library.location if self.library else None,
            'parents_album' : self.parents_album,
            'current' : self.current,
            'action' : self.action,
            'last_objs':self.last_objs,
        }
        with open("general.data", 'wb') as f:
            pickle.dump(general, f, pickle.HIGHEST_PROTOCOL)
      
    def clean(self):
        self.save()
        for th in self.io_threads:
            if th.is_alive():
                th.join()
        
        scheduler.store()
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
        def escape(e):
            if self.parents_album :
                self.back()
      
        def enter(e):
            if len(self.selected) == 1:
                tmp = self.selected.pop()
                self.selected.add( tmp )
                
                if isinstance(tmp, File):
                    self.parents_album.append(self.parents_album[-1])
                    self.display_file(tmp, self.last_k)
                else:
                    self.action = Action.pagination
                    self.parents_album.append( tmp )

                self.refresh()
        
        def delete(e):
            self.remove( self.selected )
        
        def up(e):
            if self.action in [Action.pagination, Action.pagination_albums, Action.pagination_files, Action.pagination_similarities]:
                self.select_up()
        
        def down(e):
            if self.action in [Action.pagination, Action.pagination_albums, Action.pagination_files, Action.pagination_similarities]:
                self.select_down()
        
        def left(e):
            if self.action == Action.display_file:
                self.display_previous()
            elif self.action in [Action.pagination, Action.pagination_albums, Action.pagination_files, Action.pagination_similarities]:
                self.select_previous()
        
        def right(e):
            if self.action == Action.display_file:
                self.display_next()
            elif self.action in [Action.pagination, Action.pagination_albums, Action.pagination_files, Action.pagination_similarities]:
                self.select_next()
        
        def control_press(e):
            self.selected_mod = True
            
        def control_release(e):
            self.selected_mod = False
            
        self.bind("<Escape>", escape)
        self.bind("<Return>", enter)
        self.bind("<Delete>", delete)
        
        self.bind("<KeyPress-Control_L>", control_press)
        self.bind("<KeyPress-Control_R>", control_press)
        self.bind("<KeyRelease-Control_L>", control_release)
        self.bind("<KeyRelease-Control_R>", control_release)
        
        self.bind("<Up>", up)
        self.bind("<Down>", down)
        self.bind("<Left>", left)
        self.bind("<Right>", right)
        #http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/key-names.html
        #https://stackoverflow.com/questions/16082243/how-to-bind-ctrl-in-python-tkinter
        
    def register_ticks(self):
        def _save():
            self.after(300000, _save)#ms, each 5 minutes
            self.save()
        
        def _refresh():
            self.refresh(auto=True)
            self.after(1000, _refresh) 
        
        self.after(300000, _save)
        self.after(1000, _refresh)
       
    def select(self, obj, k):
        if not self.selected_mod :
            self.selected.clear()
        
        self.last_k = k
        
        self.selected.add(obj)
        self.refresh()
    
    def select_previous(self):
        if self.last_k>-1:
            i = (self.last_k-1)%len(self.get_last_objs(self.current_pagination))
            self.select( self.get_last_objs(self.current_pagination)[i], i)
        
    def select_next(self):
        if self.last_k>-1:
            i = (self.last_k+1)%len(self.get_last_objs(self.current_pagination))
            self.select( self.get_last_objs(self.current_pagination)[i], i)
    
    def select_up(self):
        if self.last_k>-1:
            i = (self.last_k-self.mainPanel.num_x)%len(self.get_last_objs(self.current_pagination))
            self.select( self.get_last_objs(self.current_pagination)[i], i)
            
    def select_down(self):
        if self.last_k>-1:
            i = (self.last_k+self.mainPanel.num_x)%len(self.get_last_objs(self.current_pagination))
            self.select( self.get_last_objs(self.current_pagination)[i], i)

    def get_last_objs(self, id_pagination):
        return self.last_objs[id_pagination]
    
    def set_last_objs(self, id_pagination, objs):
        for k in range(len(self.last_objs), max(len(self.last_objs), id_pagination+1)):
            self.last_objs.append( [] )

        self.last_objs[id_pagination] = list(objs)
        

#### Begin Views
    def display_albums(self, albums):
        self.action = Action.pagination_albums
        
        self.set_last_objs(self.current_pagination, albums)
        
        #self.last_objs = albums
        #print(albums)
        self.mainPanel.set_pagination(albums)
        self.leftPanel.set_pagination(albums)
        self.rightPanel.set_pagination(self.selected)
        
        self.leftPanel.grid(row=0, column=0)
        self.mainPanel.grid(row=0, column=1)
        self.rightPanel.grid(row=0, column=2)
        
    def display_files(self, files):
        self.action = Action.pagination_files
        
        self.set_last_objs(self.current_pagination, files)
        #self.last_objs = files
        
        self.mainPanel.set_pagination(files)
        self.leftPanel.set_pagination(files)
        self.rightPanel.set_pagination(self.selected)
        
        self.leftPanel.grid(row=0, column=0)
        self.mainPanel.grid(row=0, column=1)
        self.rightPanel.grid(row=0, column=2)
    
    def display_similarities(self, similarities):
        self.action = Action.pagination_similarities
        
        self.set_last_objs(self.current_pagination, similarities)
        #self.last_objs = similarities

        self.mainPanel.set_similarities(similarities)
        self.leftPanel.set_pagination(similarities)
        self.rightPanel.set_pagination(similarities)
        
        self.leftPanel.grid(row=0, column=0)
        self.mainPanel.grid(row=0, column=1)
        self.rightPanel.grid(row=0, column=2)
        
        
    def display_file(self, _file, k):#position de files in self.last_objs
        self.action = Action.display_file
        self.last_k = k
        
        self.mainPanel.set_display(_file)
        self.leftPanel.set_display(_file)
        self.rightPanel.set_display(_file)
       
        self.leftPanel.grid(row=0, column=0)
        self.mainPanel.grid(row=0, column=1)
        self.rightPanel.grid(row=0, column=2)
    
    def display_previous(self):
        if self.last_k>-1:
            i = (self.last_k-1)%len(self.get_last_objs(self.current_pagination))
            self.display_file( self.get_last_objs(self.current_pagination)[i], i)
        
    def display_next(self):
        if self.last_k>-1:
            i = (self.last_k+1)%len(self.get_last_objs(self.current_pagination))
            self.display_file( self.get_last_objs(self.current_pagination)[i], i)
#### End Views               
     
## Begin Event Handling
#### Begin TopPanel
    def back(self):
        if self.parents_album:
            self.parents_album.pop()
        self.current = 0
        self.action = Action.pagination
        self.refresh()
          
    def add_album(self, name):
        if not name :
            messagebox.showerror("Error", "Invalid name for album name")

        album = Album( name )
        if self.parents_album :
            self.parents_album[-1].add_subalbum( album )
        else:
            self.library.add_album( album )
               
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
            
    def show_similarities(self, current=0):
        self.current = current
        self.action = Action.pagination_similarities

        self.display_similarities( set(self.get_last_objs(self.current_pagination)) )
          
    def show_library(self):
        self.action = Action.pagination
        self.refresh()
            
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
        self.io_threads.append( self.library.add_directory( location, self.rightPanel.actionPanel.set ) )
          
    


    def export_to(self):
        location = filedialog.askdirectory()
        if not location :
            return False
            
        if not os.path.isdir( location ):
            messagebox.showerror("Error", "No target specified")
            return False
        
        if not self.selected:
            messagebox.showerror("Error", "Nothing to export")
            return False
    
        def _export_to(objs):
            for obj in objs:
                obj.export_to(location)

        th = threading.Thread(None, _export_to, None, [copy.deepcopy( self.selected )])
        th.start()
        self.io_threads.append(th)
        
    
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
        
    def next_pagination(self):
        self.current_pagination += 1
        self.refresh()
        
    def previous_pagination(self):
        self.current -= 1
        self.current_pagination()
      
#### End BottomPanel
## End Event Handling
    
    def rename_album(self, obj, name):
        if not name :
            messagebox.showerror("Error", "Invalid name for album name")
            
        obj.rename( name )
        
        self.rightPanel.actionPanel.set()
        self.refresh()
        
    def set_cover(self, album):
        location = filedialog.askopenfilename()
        if not location :
            return None
        
        if not os.path.isfile( location ):
            messagebox.showerror("Error", "Invalid cover location")
        
        album.set_thumbnail(location)
        
    def set_cover_from(self, album, _file):
        if album:
            album.set_thumbnail( scheduler.get_file(_file.md5) )
        
    def find_similarities_inside(self):#permet de reduire la complexité, on fait du On² sur des partitions
        if self.parents_album:
            files = self.parents_album[-1].deep_files()
        else:
            files = self.library.deep_files()
        raw_similarities = find_similarities(files)

        similarities0 = collections.defaultdict( set ) # on dit que ~s est transitive
        for (f1,f2) in raw_similarities:
            similarities0[ f1 ].add(f2)
            similarities0[ f2 ].add(f1)
            
        #maintenant on recupere une seul classe déquivalence
        similarities=[]
        history = set()
        
        for f, twins in similarities0.items():
            if not history.intersection( twins ) and not f in history:
                history.add(f)
                history.update(twins)
                
                twins.add( f )
                similarities.append( twins )
        #print("Report similarities %d" % len(similarities))
        if similarities:
            self.current = 0
            self.current_pagination = 0
            self.last_objs=[[]]
            for k,twins in enumerate(similarities):
                self.set_last_objs(k, twins)
            #self.display_similarities(similarities[0])
            self.action = Action.pagination_similarities
            self.refresh()


    def set_sortname(self, name):
        self.sortname = name
        
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
        elif self.action == Action.pagination_similarities:
            self.show_similarities(self.current)
        elif self.action == Action.display_file:
            pass
        elif self.action == Action.configure_pgs:
            pass
            
    def refresh(self, auto=False):
        s = default_timer()
        if not auto :
            self.mainPanel.reset()
        self._refresh()
        #print("Refresh duration %f",  default_timer()-s)
   
    def remove_file(self, _file, refresh=False):#surtout pas de thread io
        self.parents_album[-1].remove_file( _file )
        
        self.selected.discard(_file)
    
        if refresh:
            self.refresh()
            
    def remove_album(self, album, refresh=False):#surtout pas de thread io
        album.remove_all()

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

    def exasy_configure_pgs(self):
        self.action = Action.easy_configure_pgs
        
        self.rightPanel.hide()
        self.leftPanel.hide()
        
        self.mainPanel.set_easy_scheduler()
        self.mainPanel.grid(row=0, column=1)
        
    def configure_pgs(self):
        self.action = Action.configure_pgs
        
        self.rightPanel.hide()
        self.leftPanel.hide()
        
        self.mainPanel.set_scheduler()
        self.mainPanel.grid(row=0, column=1)
        
    def save_pgs(self, data):
        with open("pgs.json", "w") as fp:
            fp.write(data)
            
        scheduler.parse()
