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

from math import ceil
from enum import Enum

from timeit import default_timer



#logging.basicConfig(
        #stream= sys.stdout,
        #format='%(asctime)s  %(levelname)s  %(filename)s %(funcName)s %(lineno)d %(message)s',
        #level=logging.DEBUG)
logging.basicConfig(
        stream= sys.stdout,
        format='%(message)s',
        level=logging.DEBUG)

def benchmark():
    def benchmark_fun(function):
        start = default_timer()
        res = function
        logging.debug((function, default_timer()-start))
        return res
    return benchmark_fun

#def benchmark(function):
    #start = default_timer()
    #res = function
    #logging.debug((function, default_timer()-start))
    #return res

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


class HandlerCache:
    def __init__(self):
        self.a_cache = {}
        self.f_cache = {}
        
        self.app = None 
    
    def album_handler(self, album):
        if not self.app:
            raise Exception("Error, handlerCache app must be initialized before usage")
        assert( self.app )
        assert( isinstance(album, Album))
            
        if album not in self.a_cache:
            self.a_cache[album] = AlbumHandler(self.app, album)
        return self.a_cache[album]
        
    def file_handler(self, _file):
        if not self.app:
            raise Exception("Error, handlerCache app must be initialized before usage")
        assert( self.app )
        assert( isinstance(_file, File))
            
        if _file not in self.f_cache:
            self.f_cache[_file] = FileHandler(self.app, _file)
        return self.f_cache[_file]

handlerCache = HandlerCache()

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
        m_import.add_command(label="Directory(recursif)", command= self.app.import_directory)
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
    def __init__(self, parent,  _file):        
        self.parent = parent
        self._file = _file
        
        self.thumbnail = None #store picture
        self.picture = None #store picture
        self.frame_thumbail = None
        
    def handle_selection(self, event):
        self.parent.select_file( self )
        
#### Begin Certificats

    def certificat_display(self):
        return (self._file.location, self._file.md5)
        
    def certificat_info(self):
        return (self._file.filename, self._file.metadata.height, 
        self._file.metadata.width, self._file.metadata.datetime)
    
    def certificat_thumbnail(self):
        return( self in self.parent.selected_files, 
        self._file.metadata.thumbnail) 
        
####End Certificats
    
    
#### Begin Make

    def make_display(self, master):
        frame = Frame(master, bg="white", width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
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
        frame.pack()
        return frame
        
    def make_info(self, master):
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
        info.pack()
        return info
    
    def make_thumbnail(self, master):
        color = "blue" if self in self.parent.selected_files else "white"
        frame = Frame(master, bg=color, width=THUMBNAIL_WIDTH+BORDER_THUMB, height=THUMBNAIL_HEIGHT+BORDER_THUMB)
        frame.pack_propagate(False)
        
        if not self.thumbnail:
            if self._file.metadata.thumbnail :
                self.thumbnail = ImageTk.PhotoImage(Image.open( self._file.metadata.thumbnail ))
            else:
                self.thumbnail = ImageTk.PhotoImage(Image.open("photo_default.png"))
        canvas = Canvas(frame, width=THUMBNAIL_WIDTH, height=THUMBNAIL_HEIGHT)
        
        canvas.bind('<Triple-Button-1>', lambda event: self.parent.display_file( self._file ) ) 
        canvas.bind('<Double-Button-1>', lambda event: self.parent.display_file( self._file ) ) 
        canvas.bind('<Button-3>', lambda event: self.parent.display_file( self._file ) ) 
        canvas.bind('<Button-1>', self.handle_selection) 

        item = canvas.create_image(0, 0, anchor=NW, image=self.thumbnail) 
        
        canvas.pack(padx=BORDER_THUMB/2, pady=BORDER_THUMB/2)
        self.frame_thumbail = frame
        return frame

#### End Make

    #def remove(self):
        #self.parent.remove_file( self._file )
        #self.parent.show_files()

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
    def __init__(self, parent, album ):
        self.parent = parent
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
      
#### Begin Certificats
        
    def certificat_info(self):
        return (self.album.name, len(self.album.subalbums), 
        len(self.album.files), len(self.album), self.album.datetime)
    
    def certificat_thumbnail(self):
        return( self in self.parent.selected_albums, 
        self.album.cover.metadata.thumbnail, self.album.name) 
        
#### End Certificats
      

#### Begin Make
    def make_info(self, master):
        info = Frame(master)
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
        
    def make_thumbnail(self, master):
        color = "blue" if self in self.parent.selected_albums else "white"
        frame = Frame(master, bg=color , width=THUMBNAIL_WIDTH+BORDER_THUMB, height=THUMBNAIL_HEIGHT+BORDER_THUMB)
        frame.pack_propagate(False)

        label = Label(frame, text=self.album.name)
        label.pack()

        if not self.thumbnail:
            if self.album.cover :
                self.thumbnail = ImageTk.PhotoImage(Image.open( self.album.cover.metadata.thumbnail ))
            else:
                self.thumbnail = ImageTk.PhotoImage(Image.open("album_default.png"))
        canvas = Canvas(frame,width=THUMBNAIL_WIDTH, height=THUMBNAIL_HEIGHT)
        
        
        def _display(event):
            self.parent.parents_album.append(self.album)
            if not self.album.files :
                self.parent.action = Action.pagination_albums
            else:
                self.parent.action = Action.pagination_files
            self.parent.refresh()
            
        canvas.bind('<Double-Button-1>', _display ) 
        canvas.bind('<Triple-Button-1>', _display ) 
        canvas.bind('<Button-3>', _display ) 
        canvas.bind('<Button-1>', lambda event : self.parent.select_album( self ) ) 
        
        canvas.create_image(0, 0, anchor=NW, image=self.thumbnail) 
    
        canvas.pack(padx=BORDER_THUMB/2, pady = BORDER_THUMB/2)
        self.frame_thumbail = frame
        return frame
    
    @recursion_protect(f=lambda x : x.album)
    def make_treeview(self, tree, objmap, parent=''):
        objmap.append( self.album)
        tree.insert(parent, 'end', str(len(objmap)-1), text=self.album.name)

        for album in self.album.subalbums.keys():
            handlerCache.album_handler(album).make_treeview(tree, objmap, str(len(objmap)-1) )

#### End Make

            
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
    pagination = 0 #programme choisi l'un des suivant
    pagination_albums = 1
    pagination_files = 2
    display_file = 3
 
class Certificat(Enum):
    add_album = 0
        
class Application(Frame):
    def __init__(self, master=None):
        Frame.__init__(self, master, bg="white", width=1300)
        handlerCache.app = self
        
        self.library = None
        self.init()
        
        self.parents_album = [] #if we are in subalbums for insertion supression etc
        
        self.selected_files = {} #store filehandler
        self.selected_albums = {} #store album handler
        self.selected_mod = False


        
        self.left_panel = Frame(self, borderwidth=1)
        self.left_panel.pack(side = LEFT)

        
        self.current = 0 #page number   
        
        self.main_panel = Frame(self, borderwidth=1)
        self.main_panel.pack(side=LEFT)
        
        self.top_panel = Frame(self.main_panel)
        self.top_panel.pack()
        self.certificat_top  = None
        
        self.center_panel = Frame(self.main_panel, borderwidth=1, width = DISPLAY_WIDTH+100, height=DISPLAY_HEIGHT+100)
        #self.center_panel.pack(side=LEFT, fill=None, expand=False)
        self.center_panel.pack()
        self.certificat_center = None
                
        
        
        self.bottom_panel = Frame(self.main_panel)
        self.bottom_panel.pack()
        self.certificat_bottom  = None
        
        self.right_panel = Frame(self,  borderwidth=1, width=400, height=700)
        self.right_panel.pack()
       
        self.right_info=Frame(self.right_panel)
        self.certificat_right_info = None
        

        self.right_action=Frame(self.right_panel)
        self.certificat_right_action=None
        
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
            self.master.after(300000, _save)#ms, each 5 minutes
            self.save()
        
        def _refresh():
            self.refresh()
            self.master.after(3000, _refresh) #ms, each 5 minutes
        
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
        self.make_pagination_right_panel()
    
    def select_album(self, albumhandler):
        if not self.selected_mod :
            self.clear_selected()
        
        albumhandler.frame_thumbail.configure(bg = "blue")
        self.selected_albums[albumhandler] = True
        self.make_pagination_right_panel()
    
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

#### Begin Views
    def display_albums(self, albums, parents_album=[]):
        if not self.library:
            return False
            
        self.action = Action.pagination_albums
        self.parents_album.extend( parents_album )

        ## CenterPanel
        certificat_center = (self.action, 
            self.parents_album[-1] if self.parents_album else None,
            self.current,
            len(albums),
            sum([id(album) for album in albums])
        )
        if certificat_center != self.certificat_center:
            logging.debug("CenterPanel repaint")
            self.certificat_center = certificat_center
            clean_frame( self.center_panel )
        
            self.make_albums_pagination(albums)
            
            self.center_panel.pack()
        ## End CenterPanel
        
        self.make_pagination(len(albums))
        
    def display_files(self, files, parents_album=[]):
        if not self.library:
            return False
            
        #self.files_to_display = files
        self.action = Action.pagination_files
        self.parents_album.extend( parents_album )
     
        ## CenterPanel
        certificat_center = (self.action, 
            self.parents_album[-1] if self.parents_album else None,
            self.current,
            len(files),
            sum([id(_file) for _file in files])
        )
        if certificat_center != self.certificat_center:
            logging.debug("CenterPanel repaint")
            self.certificat_center = certificat_center
            clean_frame( self.center_panel )
        
            self.make_files_pagination(files)
            
            self.center_panel.pack()
        ## End CenterPanel
        
        self.make_pagination(len(files))
        
        
    def display_file(self, _file):
        if not self.library:
            return False
            
        self.action = Action.display_file
        handler = handlerCache.file_handler( _file )
            
            
        ## LeftPanel
        clean_frame(  self.left_panel )
        ## End LeftPanel
        

        ## TopPanel
        certificat_top = (self.action, 
            self.parents_album[-1] if self.parents_album else None,
            _file
        )
        if certificat_top != self.certificat_top:
            logging.debug("TopPanel repaint")
            self.certificat_top = certificat_top
            clean_frame( self.top_panel )
        
            b_back = Button(self.top_panel, text="Back", command=self.show_files)
            b_back.pack(side=LEFT);
       
            def _remove():
                self.remove_file(_file, handler, True)
                self.show_files()
            b_remove = Button(self.top_panel, text="Remove", command=_remove)
            b_remove.pack(side=LEFT)
            
            self.top_panel.pack()
        ## End TopPanel
        
        ## CenterPanel
        certificat_center = (self.action, 
            self.parents_album[-1] if self.parents_album else None,
            handler.certificat_display()
        )
        if certificat_center != self.certificat_center:
            logging.debug("CenterPanel repaint")
            self.certificat_center = certificat_center
            clean_frame( self.center_panel )
            
            handler.make_display(self.center_panel)
            self.center_panel.pack()    
        ## End CenterPanel
        
        ## RightPanel
        #### InfoPanel
        certificat_info = (self.action, 
            self.parents_album[-1] if self.parents_album else None,
            handler.certificat_info()
        )
        if certificat_info != self.certificat_right_info:
            logging.debug("InfoPanel repaint")
            self.certificat_right_info = certificat_info
            clean_frame(  self.right_info )
            
            handler.make_info(self.right_info)
            self.right_info.pack()
        
        #### ActionPanel
        clean_frame( self.right_action )
        
        ## End RightPanel
        
        ## Begin BottomPanel
        clean_frame( self.bottom_panel )
        ## End BottomPanel
        
#### End Views   
     

#### Begin Make

###### Begin Pagination
    def make_files_pagination(self, files):
        nm = height*width
        offset = self.current * nm
                
        pagination = VerticalScrolledFrame(self.center_panel, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
        for i in range(height):
            for j in range(width):
                if offset + i*width + j >=  len( files ):
                    break
                handler = handlerCache.file_handler(files[ offset + i*width + j])
                handler.make_thumbnail(pagination.interior).grid(row=i, column=j)
        pagination.pack_propagate(False)
        pagination.pack()
        
    def make_albums_pagination(self, albums):
        nm = height*width
        offset = self.current * nm
        
        pagination = VerticalScrolledFrame(self.center_panel, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
        i, j =0,0
        for i in range(height):
            for j in range(width):
                if offset + i*width + j >=  len( albums ):
                    break
                handler = handlerCache.album_handler(albums[ offset + i*width + j])
                handler.make_thumbnail(pagination.interior).grid(row=i, column=j)
            if j != width-1 :
                break
        pagination.pack_propagate(False)
        pagination.pack()
        
    def make_pagination(self, number):
        ## LeftPanel
        clean_frame( self.left_panel )
        ## End LeftPanel
        
        ## TopPanel
        certificat_top = (self.action, 
            self.parents_album[-1] if self.parents_album else None)
        if certificat_top != self.certificat_top:
            logging.debug("TopPanel repaint")
            self.certificat_top = certificat_top
            clean_frame( self.top_panel )
        
            if self.parents_album : 
                b_back = Button(self.top_panel, text="Back", command= self.back )
                b_back.pack(side=LEFT)
                
            f_add_album = Frame(self.top_panel)
            f_add_album.pack(side=LEFT)
            b_add_album = Button(f_add_album, text="Add album", command= lambda _=None : self.make_add_album(f_add_album) )
            b_add_album.pack(side=LEFT)
            
            b_show_files = Button(self.top_panel, text="Show pictures", command= self.show_files )
            b_show_files.pack(side=LEFT)
            b_show_albums = Button(self.top_panel, text="Show albums", command= self.show_albums )
            b_show_albums.pack(side=LEFT)
            
            self.top_panel.pack()
        ## End TopPanel
                        
        ## BottomPanel
        certificat_bottom = (self.action, 
            self.parents_album[-1] if self.parents_album else None,
            height, width, number, self.current)
        if certificat_bottom != self.certificat_bottom:
            logging.debug("BottomPanel repaint")
            self.certificat_bottom = certificat_bottom
            clean_frame( self.bottom_panel )
        
            nm = height*width
            offset = self.current * nm
            
            label = Label(self.bottom_panel, text="Page : %d/%d" % (self.current + 1, 1 + number/nm) )
            label.pack(side=LEFT)
            
            if self.current > 0:
                b_previous = Button(self.bottom_panel, text="Previous", command=self.previous_page)
                b_previous.pack(side=LEFT)
            
            if self.current < int(float(number)/float(nm)):
                b_next = Button(self.bottom_panel, text="Next", command=self.next_page)
                b_next.pack(side=LEFT)
            
            self.bottom_panel.pack()
        ## End BottomPanel
                
        self.make_pagination_right_panel()
        
    def make_pagination_right_panel(self):
        #### InfoPanel
        certificat_info = (self.action, 
            self.parents_album[-1] if self.parents_album else None,
            
            len(self.selected_albums), 
            [handler for handler in self.selected_albums],
            sum([ len(handler.album) for handler in self.selected_albums] ),
            list(self.selected_albums.keys())[0].certificat_info() if len( self.selected_albums ) == 1 else None,
            
            len(self.selected_files), 
            [handler for handler in self.selected_files],
            list(self.selected_files.keys())[0].certificat_info() if len( self.selected_files ) == 1 else None,
        )
        if certificat_info != self.certificat_right_info:
            logging.debug("InfoPanel repaint")
            self.certificat_right_info = certificat_info
            
            clean_frame( self.right_info )
            
            self.make_pagination_right_info()
            self.right_info.pack()
        
        #### ActionPanel
        #Check tree change
        tmp_albums = self.parents_album[-1].subalbums if self.parents_album else self.library.albums
        tmp_files = self.parents_album[-1].files if self.parents_album else []
        certificat_right_action = (self.action, 
            self.parents_album[-1] if self.parents_album else None,
            self.selected_files or self.selected_albums,
            len(tmp_albums), len(tmp_files),
            sum([id(album) for album in tmp_albums]),
            sum([id(_file) for _file in tmp_files]),
            [handler for handler in self.selected_albums.keys()],
            [handler for handler in self.selected_files]
        )
        if certificat_right_action != self.certificat_right_action:
            logging.debug("ActionPanel repaint")
            self.certificat_right_action = certificat_right_action
            
            clean_frame( self.right_action )
        
            if self.selected_files or self.selected_albums:
                self.make_selection_panel(self.right_action)
            
            self.right_action.pack()
        #### End ActionPanel
    
    def make_pagination_right_info(self):
        info1 = Frame(self.right_info)
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
            
        info2 = Frame(self.right_info)
        info2.pack(pady=5)
        
        if len(self.selected_files)>1:
            label = Label(info2, text="File%s selected :" % ("s" if len(self.selected_files)>1 else "") )
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
            
    def make_selection_panel(self, action1):
        frame = Frame(action1)
        frame.pack()
        
        objmap=[]
        tree = ttk.Treeview(frame)
        tree.grid(row=0, column=0)

        for album in self.library.albums:
            handlerCache.album_handler(album).make_treeview(tree, objmap)
        
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
###### End Pagination
     
###### Begin RightPanl
 
###### End RightPanel
    def make_add_album(self, frame):
        clean_frame( frame )
        frame.pack(side=LEFT)
        
        name = StringVar() 
        name.set("Album name")
        name_entry = Entry(frame, textvariable=name, width=10)
        name_entry.pack(side=LEFT)
        
        button = Button(frame, text="Add")
        button.bind("<Button-1>", lambda event: self.add_album(name.get(), frame))
        button.pack(side=LEFT)
        
        frame.pack()
        
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
               
        clean_frame(frame)
        b_add_album = Button(frame, text="Add album", command= lambda _=None : self.make_add_album(f_add_album) )
        b_add_album.pack(side=LEFT)
        frame.pack(side=LEFT)
               
        self.action = Action.pagination_albums
        self.refresh()
     
    def show_files(self, current=0):
        self.current = current
        self.action = Action.pagination_files

        if self.parents_album :
            self.display_files( list(self.parents_album[-1].files.keys()), [])
        else:
            self.display_files([], [])
                
    def show_albums(self, current=0):
        self.current = current
        self.action = Action.pagination_albums
        
        if self.parents_album :
            self.display_albums( list(self.parents_album[-1].subalbums.keys()), [])
        else:
            self.display_albums(list(self.library.albums.keys()), [])

#### Begin TopPanel



#### Begin Menu
    def set_library_location(self, location=None):
        self.save_library()
        self.library = Library( filedialog.askdirectory() if not location else location )
        
        self.parents_album.clear()
        self.selected_files.clear()
        self.selected_albums.clear()
        
        self.action = Action.pagination
        self.refresh()

    def import_directory(self):
        location = filedialog.askdirectory()

        if not self.library:
            messagebox.showerror("Error", "Library location : not defined")
            return False
        if not location or not os.path.isdir( location ):
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
        if not location or not os.path.isdir( location ):
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
            parent_album.add_file( handler._file )
        
    def move_to(self, frame, parent_album):
        frame.destroy()
        
        for handler in self.selected_albums.keys():
            parent_album.add_subalbum( handler.album )
            self.remove_album( handler.album )
            
        for handler in self.selected_files.keys():
            parent_album.add_file( handler._file )
            self.remove_file( handler._file )
        
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
     
        
   
    def init(self):
        pass
    
    def rename_album(self, name):
        if not name :
            messagebox.showerror("Error", "Invalid name for album name")
            
        (list(self.selected_albums)[0].album).rename( name )

        self.show_albums()
        
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
            if not self.parents_album:
                self.albums_to_display = list(self.library.albums)
            else:
                self.albums_to_display = list(self.parents_album[-1].subalbums)
                
            self.show_albums(self.current)
        elif self.action == Action.display_file:
            pass
        
    def refresh(self):
        s = default_timer()
        self._refresh()
        print("Refresh duration %f",  default_timer()-s)
    def remove_file(self, _file, handler=None, refresh=False):#surtout pas de thread io
        self.parents_album[-1].remove_file( _file, self.library.files )
        
        if handler in self.selected_files:
            del self.selected_files[handler]
        
        if refresh:
            self.refresh()
            
    def remove_album(self, album, handler=None, refresh=False):#surtout pas de thread io
        album.remove_all(self.library.files)

        if self.parents_album:
            self.parents_album[-1].remove_subalbum( album )
        else:
            self.library.remove_album( album )
        
        if handler in self.selected_albums:
            del self.selected_albums[handler]
           
        if refresh:
            self.refresh()
            
window = Tk()

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
