#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
 
 
#http://apprendre-python.com/page-tkinter-interface-graphique-python-tutoriel
#https://docs.python.org/3.4/library/tkinter.html
#http://tkinter.unpythonic.net/wiki/Widgets
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
from enum import Enum
THUMBNAIL_HEIGHT = 128
THUMBNAIL_WIDTH = 128
DISPLAY_HEIGHT = 480
DISPLAY_WIDTH = 640

BORDER_THUMB = 4

height= 5
width = 5 #must be calculated en fonction de la resolution courrante

def test(album_appp):
    messagebox.showerror("Test", "Test testttestste")

exts   = [ "png", "jpeg", "jpg", "mov", "mp4", "mpg", "thm", "3gp"]
img_exts = [ "png", "jpeg", "jpg"]
mv_exts = ["mov", "mp4", "mpg", "thm", "3gp"]

def check_ext(filename, exts_=exts):
    currentExt  = filename.split( '.' )[ -1 ]
    return currentExt.lower() in exts_

def clean_frame(frame):
    for widget in frame.winfo_children():
        widget.destroy()


# http://tkinter.unpythonic.net/wiki/VerticalScrolledFrame
class VerticalScrolledFrame(Frame):
    """A pure Tkinter scrollable frame that actually works!

    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
    * This frame only allows vertical scrolling
    
    """
    def __init__(self, parent, *args, **kw):
        Frame.__init__(self, parent, *args, **kw)            

        # create a canvas object and a vertical scrollbar for scrolling it
        vscrollbar = Scrollbar(self, orient=VERTICAL)
        vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        canvas = Canvas(self, bd=0, highlightthickness=0,
                        yscrollcommand=vscrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
        vscrollbar.config(command=canvas.yview)

        # reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.interior = interior = Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=interior,
                                           anchor=NW)

        # track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(event):
            # update the scrollbars to match the size of the inner frame
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the canvas's width to fit the inner frame
                canvas.config(width=interior.winfo_reqwidth())
        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())
        canvas.bind('<Configure>', _configure_canvas)

        return
        
class TopMenu(Menu):
    def __init__(self, master=None, app=None):
        Menu.__init__(self, master)
        
        self.app = app
        
        self.make()
    
    def make(self):
        self.make_file()
        self.make_import()
        self.make_export()

    def make_file(self):
        m_file = Menu(self, tearoff=0)
        m_file.add_command(label="Open", command= self.app.set_library_location)
        m_file.add_command(label="Save lib", command= self.app.save_library)
        m_file.add_separator()
        m_file.add_command(label="Quit", command= self.master.quit)
        self.add_cascade(label="File", menu=m_file)
    
    def make_import(self):
        m_import = Menu(self, tearoff=0)
        m_import.add_command(label="Directory(recursif)", command= self.app.add_directory)
        self.add_cascade(label="Import", menu=m_import)

    def make_export(self):
        m_export = Menu(self, tearoff=0)
        #m_export.add_command(label="Export all", command= self.app.export_all)
        m_export.add_command(label="Export to", command= self.app.export_to)
        self.add_cascade(label="Export", menu=m_export)

class FileMetadata: #data extracted et en richie
    def __init__(self, parent = None):
        self.parent = parent
       
        self.datetime  = None
        self.thumbnail  = None
        self.year = None
        self.month = None
        self.width, self.height = 0, 0
    
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
                
            if not self.datetime:
                tmp = ""
                for tag, value in info.items():
                    decoded = TAGS.get(tag, tag)
                    tmp += decoded + "\n"
                logging.debug("tag not found in %s" % tmp)
            
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


def io_protect(default=None):
    def decorator(function):
        def new_function(self, *args, **kwargs):
            res = default
            with self.io_lock:
                res = function(self, *args, **kwargs)
            return res
        return new_function
    return decorator

class File:
    def __init__(self, filename=None, location=None):
        self.filename = filename
        self.location = location
        self.md5 = None
        self.metadata = FileMetadata(self)      
        self.extracted = False  
        
        if location and filename and not self.extracted:
            self.extract()
        
        self.garbage_number = 0 #if 0 then data suppressed
        
        self.io_lock = threading.Lock() #pour gérer les export concurrant à une suppression si wait vérouiller on ne peut pas supprimer

    def __deepcopy__(self, memo):
        new = File(self.filename, self.location)
        new.md5 = self.md5
        new.metadata = self.metadata.__deepcopy__(None, new)
        new.garbage_number = None #sort du garbage collector si on le copie
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
        self.md5 = hashlib.md5(open(self.location, "rb").read()).hexdigest()
        self.metadata.extract()
    
    def create_thumbnails(self):
        if check_ext(self.filename, img_exts):
            im = Image.open( self.location )
            im.thumbnail( (THUMBNAIL_HEIGHT, THUMBNAIL_WIDTH) )
            im.save(self.metadata.thumbnail, "JPEG")
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

class FileHandler:
    def __init__(self, parent, master, _file):        
        self.parent = parent
        self.master = master
        self._file = _file
        
        self.thumbnail = None #store picture
        self.picture = None #store picture
        self.frame_thumbail = None
        
    def handle_selection(self, event):
        self.parent.select_file( self )
        
    def make_thumbnail(self):
        frame = Frame(self.master, bg="white", width=THUMBNAIL_WIDTH+BORDER_THUMB, height=THUMBNAIL_HEIGHT+BORDER_THUMB)
        frame.pack_propagate(False)

        if self._file.metadata.thumbnail :
            photo = ImageTk.PhotoImage(Image.open( self._file.metadata.thumbnail ))
        else:
            photo = ImageTk.PhotoImage(Image.open("photo_default.png"))
        canvas = Canvas(frame, width=THUMBNAIL_WIDTH, height=THUMBNAIL_HEIGHT)
        
        canvas.bind('<Triple-Button-1>', lambda event: self.parent.display_picture( self._file ) ) 
        canvas.bind('<Double-Button-1>', lambda event: self.parent.display_picture( self._file ) ) 
        canvas.bind('<Button-3>', lambda event: self.parent.display_picture( self._file ) ) 
        canvas.bind('<Button-1>', self.handle_selection) 
        
        self.thumbnail = photo 
        item = canvas.create_image(0, 0, anchor=NW, image=photo) 
        
        canvas.pack(padx=BORDER_THUMB/2, pady=BORDER_THUMB/2)
        self.frame_thumbail = frame
        return frame

    def make_display(self):
        frame = Frame(self.master, bg="white", width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
        
        menu=Frame(frame)
        b_back = Button(menu, text="Back", command=self.parent.show_files)
        b_back.pack(side=LEFT);
        b_remove = Button(menu, text="Remove", command=self.remove)
        b_remove.pack(side=LEFT)
        menu.pack()
        
        im=Image.open( self._file.location )
        
        width, height = im.size
        ratio = float(width)/float(height)
        if float(width)/float(DISPLAY_WIDTH) < float(height)/float(DISPLAY_HEIGHT):
            height = min(height,DISPLAY_HEIGHT)
            width = int(ratio * height)
        else:
            width = min(width,DISPLAY_HEIGHT)
            height = int(width / ratio)

        self.picture = ImageTk.PhotoImage(im.resize((width, height), Image.ANTIALIAS))
        
        canvas = Canvas(frame, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
        canvas.bind('<Escape>', lambda event: self.parent.show_files ) 
        item = canvas.create_image(0, 0, anchor=NW, image=self.picture) 

        canvas.pack()
        
        return frame
        
    def make_info(self, master=None):
        master = master if master else self.master
        info = Frame(master) 
        info.pack()

        name = Label(info, text=self._file.filename )
        name.pack()
        
        number_fil = Label(info, text="Height : %d" % self._file.metadata.height)
        number_fil.pack()
        
        number_rec = Label(info, text="Width : %d" % self._file.metadata.width)
        number_rec.pack()
        
        date = Label(info, text="Datetime : %s" % time.strftime( "%Y-%d-%m", self._file.metadata.datetime) )
        date.pack()
        
        return info
    
    def remove(self):#from album
        #if messagebox.askyesno("Warning", "Do you really want to delete this file?"):
        self.parent.remove_file( self._file )
        self.parent.show_files()

def recursion_protect(default=None, f= (lambda x:x)):
    def decorator(function):
        history = {}
        def protect_function(self, *args, **kwargs):
            if f(self) not in history :
                history[f(self)] = True
                tmp = function(self, *args, **kwargs)
                history.clear()
                return tmp
            else:
                history.clear()
                return default
        return protect_function
    return decorator

class Album: #subalbums not fully implemented
    def __init__(self, name=None, datetime=None):
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
     
class AlbumHandler:
    def __init__(self, parent, master, album ):
        self.parent = parent
        self.master = master
        self.album = album
    
        #Page handling
        self.w_length = 5#in file
        self.h_height = 5#in file
        self.current = 0
    
        self.thumbnail = None
        self.frame_thumbail = None
    
    def delete(self):
        if messagebox.askyesno("Warning", "Do you really want to delete this ? It cannot be cancelled") :
            self.parent.remove_album( self.album )
        else:
            return
      
    def make_thumbnail(self):
        frame = Frame(self.master, bg="white", width=THUMBNAIL_WIDTH+BORDER_THUMB, height=THUMBNAIL_HEIGHT+BORDER_THUMB)
        frame.pack_propagate(False)

        label = Label(frame, text=self.album.name)
        label.pack()

        if self.album.cover :
            photo = ImageTk.PhotoImage(Image.open( self.album.cover.metadata.thumbnail ))
        else:
            photo = ImageTk.PhotoImage(Image.open("album_default.png"))
        canvas = Canvas(frame,width=THUMBNAIL_WIDTH, height=THUMBNAIL_HEIGHT)
        
        
        def display(event):
            if not self.album.files :
                self.parent.display_albums( list( self.album.subalbums.keys()),  [self.album] )
            else:
                self.parent.display_files( list( self.album.files.keys()),  [self.album] )
        #canvas.bind('<Double-Button-1>', lambda event: self.parent.display_albums( list( self.album.subalbums.keys()),  [self.album] ) ) 
        #canvas.bind('<Triple-Button-1>', lambda event: self.parent.display_albums( list( self.album.subalbums.keys()),  [self.album] ) ) 
        #canvas.bind('<Button-3>', lambda event: self.parent.display_albums( list( self.album.subalbums.keys()),  [self.album] ) ) 
        canvas.bind('<Double-Button-1>', display ) 
        canvas.bind('<Triple-Button-1>', display ) 
        canvas.bind('<Button-3>', display ) 
        canvas.bind('<Button-1>', lambda event : self.parent.select_album( self ) ) 
        
        self.thumbnail= photo 
        item = canvas.create_image(0, 0, anchor=NW, image=photo) 
    
        canvas.pack(padx=BORDER_THUMB/2, pady = BORDER_THUMB/2)
        self.frame_thumbail = frame
        return frame
    
    def make_info(self, master=None):
        master = master if master else self.master
        info = Frame(master) #à migrer dans AlbumHandler, et dedup des handlers pas la peine  dans crée un à chaque fois 
        info.pack()

        name = Label(info, text=self.album.name )
        name.pack()
        
        number_sub = Label(info, text="Subalbums : %d" % len(self.album.subalbums))
        number_sub.pack()
        
        number_fil = Label(info, text="Files : %d" % len(self.album.files))
        number_fil.pack()
        
        number_rec = Label(info, text="All : %d" % len(self.album))
        number_rec.pack()
        
        date = Label(info, text="Datetime : %s" % time.strftime( "%Y-%d-%m", self.album.datetime) )
        date.pack()
        
        return info
        
    @recursion_protect(f=lambda x : x.album)
    def make_treeview(self, tree, objmap, parent=''):
        objmap.append( self.album)
        tree.insert(parent, 'end', str(len(objmap)-1), text=self.album.name)

        for album in self.album.subalbums.keys():
            AlbumHandler(self, self, album).make_treeview(tree, objmap, str(len(objmap)-1) )
            
class Library:
    def __init__(self, location, load=True):
        if load and not os.path.isdir( location ):
            messagebox.showerror("Error", "Library location : invalid")
        
        self.files = {} # ordered by hash
        self.albums = {} #orderder by id
        self.inner_albums = {}#years, month 
        
        self.io_lock = threading.Lock()
        
        self.location = location
        if self.location :
            self.load()
        
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
        
        if (year, month) not in self.inner_albums or not self.inner_albums[ (year, month) ].alive():
            if year not in self.inner_albums or not self.inner_albums[ year ].alive():
                y_album = Album( year )
                self.inner_albums[ year ] = y_album
                self.albums[ y_album ] = True
            else:
                y_album = self.inner_albums[ year ]
            
            m_album = Album( month )
            y_album.add_subalbum( m_album )

            self.inner_albums[ (year, month) ] = m_album
        
        self.inner_albums[ (year, month) ].add_file( _file )
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
        self.albums[ album ] =True
        
    @io_protect()
    def remove_album(self, album):
        if album in self.albums:
            del self.albums[ album ]
            
        album.died = True
 
class Action(Enum):
    pagination_albums = 1
    pagination_files = 2
    display_file = 3
 
        
class Application(Frame):
    def __init__(self, master=None):
        Frame.__init__(self, master, bg="white")
        Label(self, text="Frame 1").pack(padx=10, pady=10)

        self.library = None
        self.init()
        
        self.files_to_display = []
        self.albums_to_display = []
        self.parents_album = [] #if we are in subalbums for insertion supression etc
        
        self.selected_files = {} #store filehandler
        self.selected_albums = {} #store album handler
        self.selected_mod = False

        self.left_frame = Frame(self, borderwidth=1)
        self.left_frame.pack(side=LEFT)
        self.inner_left_frame = None
        
        self.current = 0 #page number   
        self.main_frame = Frame(self, borderwidth=1, width = DISPLAY_WIDTH+100, height=DISPLAY_HEIGHT+100)
        self.main_frame.pack(side=LEFT)
        self.inner_main_frame = None
        
        self.right_frame = Frame(self, borderwidth=1)
        self.right_frame.pack(side=LEFT)
        self.inner_right_frame = None
        
        self.last_pagination = None
        self.action = Action.pagination_albums
        
        self.load()
        self.bind()
        
        self.io_threads=[]
        self.register()
        
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
                    
                self.files_to_display = general["files_to_display"]
                self.albums_to_display = general["albums_to_display"]
                self.parents_album = general["parents_album"]
                self.current = general["current"]
                self.last_pagination =[None, self.show_albums, self.show_files][general["last_pagination"]]
        
        if not self.last_pagination and self.library:
            self.albums_to_display = list( self.library.albums.keys() ) 
            self.show_albums()
        elif self.last_pagination:
            self.last_pagination(self.current)
        
    def store(self):
        general={
            'library_location' : self.library.location if self.library else None,
            'files_to_display' : self.files_to_display,
            'albums_to_display' : self.albums_to_display,
            'parents_album' : self.parents_album,
            'current' : self.current,
            'last_pagination' : {None:0, self.show_albums:1, self.show_files:2}[self.last_pagination]
        }
        with open("general.data", 'wb') as f:
            pickle.dump(general, f, pickle.HIGHEST_PROTOCOL)
        
    def bind(self):
        def _keypress_event(event):
            if event.keycode == 37 or event.keycode == 105: #ctrl
                self.selected_mod = True
        
        def _keyrelease_event(event): 
            if event.keycode == 37 or event.keycode == 105: #ctrl
                self.selected_mod = False
                
        def escape(e):
            if self.parents_album :
                self.back()
                
        self.master.bind("<Escape>", escape)
        self.master.bind("<KeyPress>", _keypress_event)
        self.master.bind("<KeyRelease>", _keyrelease_event)
        
    def register(self):
        def _save():
            self.master.after(300000, _save)
            self.save()
        
        def _refresh():
            print("refresg")    
            self.master.after(3000, _refresh) #ms, each 5 minutes
            self.refresh()
        
        self.master.after(300000, _save)
        self.master.after(3000, _refresh)
        
    def clear_selected(self):
        try: #if already deleted by window,therefore we can keep the hisotry selection after changing page (except if we o nex select)
            for handler in self.selected_files:
                if handler.frame_thumbail:
                    handler.frame_thumbail.configure(bg="white")
        except Exception as e:
            pass
            
        try:
            for handler in self.selected_albums:
                if handler.frame_thumbail:
                    handler.frame_thumbail.configure(bg="white")
        except Exception as e:
            pass
        
        self.selected_files.clear()
        self.selected_albums.clear()
        
    def select_file(self, filehandler):
        if not self.selected_mod :
            self.clear_selected()
        
        filehandler.frame_thumbail.configure(bg = "blue")
        self.selected_files[filehandler] = True
        self.make_right_panel()
    
    def select_album(self, albumhandler):
        if not self.selected_mod :
            self.clear_selected()
        
        albumhandler.frame_thumbail.configure(bg = "blue")
        self.selected_albums[albumhandler] = True
        self.make_right_panel()
    
    def clean(self):
        self.save()
        for th in self.io_threads:
            if th.is_alive():
                th.join()
      
    def save(self):
        self.io_threads = [ th for th in self.io_threads if th.is_alive ]                
        self.save_library()
        self.store()
    
    def save_library(self):
        if self.library :
            t = threading.Thread(None, (lambda lib : lib.store()), None, (copy.deepcopy(self.library),) )#snapshot
            t.start()
            self.io_threads.append(t)
    
    def set_main_frame(self, frame):
        if self.main_frame:
            self.main_frame.destroy()
        raise Exception("")
        self.main_frame = frame

    def preprocess(self):
        if not self.library:
            return False
            
        if self.inner_main_frame :
            self.inner_main_frame.destroy()
            
        self.inner_main_frame = Frame( self.main_frame, bg="white")
        return True
        
    def postprocess(self):
        self.inner_main_frame.pack()

    def display_albums(self, albums, parents_album=[]):
        self.clean_sides()

        if not self.preprocess() :
            return None
            
        self.albums_to_display = albums
        self.parents_album.extend( parents_album )
        
        self.make_pagination(self.make_albums_pagination)
        
        self.postprocess()
        self.last_pagination = self.show_albums
        self.action = Action.pagination_albums
        
    def display_files(self, pictures, parents_album=[]):
        self.clean_sides()

        if not self.preprocess() :
            return None
            
        self.files_to_display = pictures
        self.parents_album.extend( parents_album)
     
        self.make_pagination(self.make_pictures_pagination)
        
        self.postprocess()
        self.last_pagination = self.show_files
        self.action = Action.pagination_files
        
    def display_picture(self, picture):
        self.clean_sides()

        if not self.preprocess() :
            return None
            
        frame = FileHandler(self, self.inner_main_frame, picture).make_display()
        self.inner_right_frame = FileHandler(self, self.inner_main_frame, picture).make_info()
        self.inner_right_frame.pack()
        frame.pack()
        
        self.parents_album.append( self.parents_album[-1] )
        self.postprocess()
        self.action = Action.display_file
        
    def set_library_location(self, location=None):
        self.library = Library( filedialog.askdirectory() if not location else location )
        
        self.albums_to_display = list( self.library.albums.keys() ) 
        self.show_albums()
        
    def init(self):
        pass
    
    def add_directory(self):
        location = filedialog.askdirectory()

        if not self.library:
            messagebox.showerror("Error", "Library location : not defined")
            return False
        if not location or not os.path.isdir( location ):
            messagebox.showerror("Error", "Source location : not defined")
            return False
        self.io_threads.append( self.library.add_directory( location ) )
              
    def export_to(self):
        location = filedialog.askdirectory()
        if not location or not os.path.isdir( location ):
            messagebox.showerror("Error", "No target specified")
            return False
        
        if not self.selected_albums and not self.selected_files:
            messagebox.showerror("Error", "Nothing to export")
            return False
        
        
        def _export_to(files, albums):
            for _file in files:
                _file.export_to(location)
                _file.io_lock.release()
                
            for album in albums:
                album.export_to(location)
             
        files = copy.deepcopy( [handler._file for handler in self.selected_files] )
        albums = copy.deepcopy( [handler.album for handler in self.selected_albums])
        
        for _file in files:
            _file.io_lock.acquire()

        th = threading.Thread(None, _export_to, None, ( files, albums))
        th.start()
        self.io_threads.append(th)
        
    def show_files(self, current=0):
        self.current = current
        
        if self.parents_album :
            self.display_files( list(self.parents_album[-1].files.keys()), [])
        else:
            self.display_files([], [])
        
        self.last_pagination = self.show_files
        self.action = Action.pagination_files
        
    def show_albums(self, current=0):
        self.current = current
        
        self.display_albums(self.albums_to_display, [])
    
        self.last_pagination = self.show_albums
        self.action = Action.pagination_albums
     
    def clean_sides(self):
        if self.inner_right_frame:
            self.inner_right_frame.destroy()
            
        if self.inner_left_frame:
            self.inner_left_frame.destroy()
            
    def back(self):
        self.files_to_display = []
        self.albums_to_display = []
        self.parents_album.pop()
        
        self.clean_sides()
        
        if not self.parents_album:
            self.albums_to_display = list(self.library.albums)
        else:
            self.albums_to_display = list(self.parents_album[-1].subalbums)
        
        self.show_albums()

    def make_pictures_pagination(self):
        nm = height*width
        offset = self.current * nm
                
        pagination = VerticalScrolledFrame(self.inner_main_frame, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
        for i in range(height):
            for j in range(width):
                if offset + i*width + j >=  len( self.files_to_display ):
                    break
                tmp = FileHandler(self, pagination.interior, self.files_to_display[ offset + i*width + j]).make_thumbnail()
                tmp.grid(row=i, column=j)
        pagination.pack_propagate(False)
        pagination.pack()
        
        return len(self.files_to_display)
        
    def make_albums_pagination(self):
        nm = height*width
        offset = self.current * nm
        
        pagination = VerticalScrolledFrame(self.inner_main_frame, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
        i, j =0,0
        for i in range(height):
            for j in range(width):
                if offset + i*width + j >=  len( self.albums_to_display ):
                    break
                tmp = AlbumHandler(self, pagination.interior, self.albums_to_display[ offset + i*width + j]).make_thumbnail()
                tmp.grid(row=i, column=j)
            if j != width-1 :
                break
        pagination.pack_propagate(False)
        pagination.pack()
        return len(self.albums_to_display)
        
    def make_pagination(self, inner_make):
        ### Begin TopMenu ###
        menu = Frame(self.inner_main_frame)   
        if self.parents_album : 
            b_back = Button(menu, text="Back", command= self.back )
            b_back.pack(side=LEFT)
 
        b_add_dir = Button(menu, text="Add album", command= self.build_add_album )
        b_add_dir.pack(side=LEFT)
        b_show_files = Button(menu, text="Show pictures", command= self.show_files )
        b_show_files.pack(side=LEFT)
        b_show_albums = Button(menu, text="Show albums", command= self.show_albums )
        b_show_albums.pack(side=LEFT)
        menu.pack()
        ### End TopMenu ###
        
        number = inner_make()
        
        ### Begin BottomMenu ###
        nm = height*width
        offset = self.current * nm
        
        nav = Frame( self.inner_main_frame, bg="white")
        label = Label(nav, text="Page : %d/%d" % (self.current + 1, 1 + number/nm) )
        label.pack(side=LEFT)
        
        if self.current > 0:
            b_previous = Button(nav, text="Previous", command=self.previous_page)
            b_previous.pack(side=LEFT)
        
        if self.current < int(number/nm):
            b_next = Button(nav, text="Next", command=self.next_page)
            b_next.pack(side=LEFT)
        nav.pack() 
        nav.pack()
        ### End BottomMenu ###
        
        self.make_right_panel()
        
    def make_right_panel(self):
        if self.inner_right_frame:
            self.inner_right_frame.destroy()
        
        self.inner_right_frame = Frame( self.right_frame)
        self.inner_right_frame.pack()
        
        ### Begin right panel ###
        info1 = Frame(self.inner_right_frame)
        info1.pack(pady=5)

        if len(self.selected_albums)>1 :
            label = Label(info1, text="Album%s selected :" % ("s" if len(self.selected_albums)>1 else "") )
            label.pack()
            
            number = Label(info1, text="Number : %d " % len(self.selected_albums) )
            number.pack()
            
            deep_number = Label(info1, text="Number : %d " % sum([ len(handler.album) for handler in self.selected_albums] ) )
            deep_number.pack()
            
            sep2 = ttk.Separator( info1, orient='horizontal')
            sep2.pack(padx = 5, pady = 5)
        elif len(self.selected_albums)==1 :
            handler = list(self.selected_albums.keys())[0]
            
            label = Label(info1, text="Album informations :")
            label.pack()
            
            album_info = handler.make_info(info1)
            album_info.pack()
            
            
            f_rename = Frame(info1)
            f_rename.pack(side=LEFT)
            
            b_rename = Button(f_rename, text="Rename", command= (lambda _=None :self.make_rename_album(handler, f_rename)) )
            b_rename.pack()
            b_rm_album = Button(info1, text="Remove", command= (lambda _=None : self.remove_album(handler.album, handler, True)) )
            b_rm_album.pack()
        else:
            pass
            
        info2 = Frame(self.inner_right_frame)
        info2.pack(pady=5)
        
        if len(self.selected_files)>1:
            handler = Label(info2, text="File%s selected :" % ("s" if len(self.selected_files)>1 else "") )
            label.pack()
            
            number = Label(info2, text="Number : %d " % len(self.selected_files) )
            number.pack()
            
            sep2 = ttk.Separator( info2, orient='horizontal')
            sep2.pack(padx = 5, pady = 5)
        elif len(self.selected_files)==1 :
            handler = list(self.selected_files.keys())[0]
            
            label = Label(info1, text="File informations :")
            label.pack()
            
            file_info = handler.make_info(info1)
            file_info.pack()
            
            b_rm_file = Button(info2, text="Remove", command= (lambda _=None : self.remove_file(handler._file, handler, True)) )
            b_rm_file.pack()
        else:
            pass
            
        action1 = Frame(self.inner_right_frame)
        action1.pack()
        if self.selected_files or self.selected_albums:
            self.make_selection_panel(action1)
           
    def make_selection_panel(self, action1):
        frame = Frame(action1)
        frame.pack()
        
        objmap=[]
        tree = ttk.Treeview(frame)
        tree.grid(row=0, column=0)

        for album in self.library.albums:
            AlbumHandler(self, tree, album).make_treeview(tree, objmap)
        
        ysb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        xsb = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
        
        tree.configure(yscroll=ysb.set, xscroll=xsb.set)
        ysb.grid(row=0, column=1, sticky='ns')
        xsb.grid(row=1, column=0, sticky='ew')
        
        b_frame = Frame(frame)
        b_frame.grid(row=2, column=0)
        
        b_addto = Button(b_frame, text="Add to", command = lambda _=None : self.add_to( frame, objmap[int(tree.focus())] if tree.focus() else None ))
        b_addto.grid(row=2, column=0)
        b_copyto = Button(b_frame, text="Copy to", command = lambda _=None : self.copy_to( frame, objmap[int(tree.focus())] if tree.focus() else None ))
        b_copyto.grid(row=2, column=1)
        b_copyto = Button(b_frame, text="Move to", command = lambda _=None : self.move_to( frame, objmap[int(tree.focus())] if tree.focus() else None ))
        b_copyto.grid(row=2, column=2)
       
    def add_to(self, frame, parent_album):
        frame.destroy()
        
        for handler in self.selected_albums.keys():
            parent_album.add_subalbum( handler.album )
            
        for handler in self.selected_files.keys():
            parent_album.add_file( handler._file )
            
    def copy_to(self, frame, parent_album):
        frame.destroy()
        
        for handler in self.selected_albums.keys():
            parent_album.add_subalbum( copy.deepcopy( handler.album ) )
            
        for handler in self.selected_files.keys():
            parent_album.add_file( handler._file )#jamais de deepcopy sur une image ..... sinon plus de grabage collector foncionnel....
        
    def move_to(self, frame, parent_album):
        frame.destroy()
        
        for handler in self.selected_albums.keys():
            parent_album.add_subalbum( handler.album )
            self.remove_album( handler.album )
            
        for handler in self.selected_files.keys():
            parent_album.add_file( handler._file )
            self.remove_file( handler._file )
        
    def build_add_album(self):
        if self.inner_left_frame :
            self.inner_left_frame.destroy()
            
        self.inner_left_frame = Frame(self.left_frame)
        
        name = StringVar() 
        name.set("Album name")
        name_entry = Entry(self.inner_left_frame, textvariable=name, width=10)
        name_entry.pack(side=LEFT)
        
        button = Button(self.inner_left_frame, text="Add")
        button.bind("<Button-1>", lambda event: self.add_album(name.get()))
        button.pack(side=LEFT)
        self.inner_left_frame.pack()
        
    def make_rename_album(self, handler, frame):
        clean_frame( frame )
        frame.pack(side=TOP)
        
        name = StringVar() 
        name.set(handler.album.name)
        name_entry = Entry(frame, textvariable=name, width=15)
        name_entry.pack(side=LEFT)
        
        button = Button(frame, text="Rename")
        button.bind("<Button-1>", lambda event: self.rename_album(name.get()))
        button.pack(side=LEFT)
        
    def add_album(self, name):
        if not name :
            messagebox.showerror("Error", "Invalid name for album name")

        album = Album( name )
        if self.parents_album :
            self.parents_album[-1].add_subalbum( album )
        else:
            self.library.add_album( album )
                
        self.albums_to_display.append( album )
        self.show_albums()
        
    def rename_album(self, name):
        if not name :
            messagebox.showerror("Error", "Invalid name for album name")
            
        (list(self.selected_albums)[0].album).rename( name )

        self.show_albums()
        
    def refresh(self):
        if self.action == Action.pagination_files:
            self.show_files(self.current)
        elif self.action == Action.pagination_albums:
            if not self.parents_album:
                self.albums_to_display = list(self.library.albums)
            else:
                self.albums_to_display = list(self.parents_album[-1].subalbums)
                
            self.show_albums(self.current)
        elif self.action == Action.display_file:
            pass
        
    def next_page(self):
        self.current += 1
        self.refresh()
        
    def previous_page(self):
        self.current -= 1
        self.refresh()
        
    def remove_file(self, _file, handler=None, refresh=False):#surtout pas de thread io
        self.parents_album[-1].remove_file( _file, self.library.files )
        
        if handler in self.selected_files:
            del self.selected_files[handler]
        
        if _file in self.files_to_display:
            self.files_to_display.remove(_file)
        

        self.refresh()
            
    def remove_album(self, album, handler=None, refresh=False):#surtout pas de thread io
        album.remove_all(self.library.files)

        if self.parents_album:
            self.parents_album[-1].remove_subalbum( album )
        else:
            self.library.remove_album( album )
        
        if handler in self.selected_albums:
            del self.selected_albums[handler]
        
        if album in self.albums_to_display:#O(n), cannot be improve ..
            self.albums_to_display.remove( album )
            
        self.refresh()
            
window = Tk()
#window.bind("<KeyPress>", lambda event: print("key pressed %d" % event.keycode))
#window.bind("<Button-1>", lambda event: print("clic pressed"))
app = Application( master=window)
app.pack(padx=30, pady=30)

menubar = TopMenu( window, app)

progress=ttk.Progressbar(window, mode="determinate", length="500", value=50, maximum=100)
progress.step(40)

progress.pack(side=BOTTOM, padx=30, pady=30)
progress.value= 90
window.config(menu=menubar)


def on_closing():
    app.clean()
    
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        window.destroy()

window.protocol("WM_DELETE_WINDOW", on_closing)
window.mainloop()
