from tkinter import * 
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox

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

from lipyc.panels.Panel import Panel, VScrolledPanel
from lipyc.Album import Album
from lipyc.File import File
from lipyc.config import *



class TopPanel(Panel):
    def __init__(self, app, master, max_buttons, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        
        self.app = app
        
        self.buttons = []
        self.buttons_text = ["" for k in range(max_buttons)]
        self.buttons_callback = [None for k in range(max_buttons)]
            
        for k in range(max_buttons):
            tmp = Button(self)
            tmp.grid(row=k, column=max_buttons)
            tmp.grid_forget()
            
            self.buttons.append(tmp)

    def set_buttons(self, texts, callbacks ):
        if self.buttons_text == texts and self.buttons_callback == callbacks:
            return None
        
        for k in range(0, min(len(texts), len(self.buttons))):
            self.buttons[k].configure( text=texts[k], command=callbacks[k] )
            self.grid()
            
            self.buttons[k].grid(row=0, column=k)
            self.buttons_text[k] = texts[k]
            self.buttons_callback[k] = callbacks[k]
        
        for k in range(len(texts), len(self.buttons)):
            self.buttons[k].grid_forget()
            self.buttons_text[k] = ""
            self.buttons_callback[k] = None
       
    def set_pagination(self):        
        texts=["Back"] if self.app.parents_album else []
        texts.extend([
            "Add album",
            "Show files",
            "Show albums"
        ])
        
        callbacks=[self.app.back] if self.app.parents_album else []
        callbacks.extend([
            lambda _=None : self.app.make_add_album(self),
            self.app.show_files,
            self.app.show_albums
        ])
        
        self.set_buttons( texts, callbacks)

    def set_display(self):        
        texts=["Back"]
        callbacks=[self.app.back]
        
        self.set_buttons( texts, callbacks)
        
    def refresh(self):
        None
        
class PaginationBottomPanel(Panel):
    def __init__(self, app, master, max_buttons, max_tiles, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        
        self.app = app
        self.max_tiles = max_tiles
        
        self.label = Label(self)
        self.label_text = []
        
        self.buttons = []
        self.buttons_text = ["" for k in range(max_buttons)]
        self.buttons_callback = [None for k in range(max_buttons)]
            
        self.label.grid(row=0, column=0)
        self.label.grid_forget()
        
        for k in range(max_buttons):
            tmp = Button(self)
            tmp.grid(row=k+1, column=max_buttons)
            tmp.grid_forget()
            
            self.buttons.append(tmp)
            
        self.number = -1
        self.current = -1
            
    def set_label(self, text):
        self.label.configure(text=text)
    
    def set_buttons(self, texts, callbacks ):
        if self.buttons_text == texts and self.buttons_callback == callbacks:
            return None
        
        for k in range(0, min(len(texts), len(self.buttons))):
            self.buttons[k].configure( text=texts[k], command=callbacks[k] )
            self.grid()
            
            self.buttons_text[k] = texts[k]
            print( self.buttons_callback[k] )
            self.buttons_callback[k] = callbacks[k]
        
        for k in range(len(texts), len(self.buttons)):
            self.buttons[k].grid_forget()
            self.buttons_text[k] = ""
            self.buttons_callback[k] = None
    
    def set_pagination(self, number):
        if self.current == self.app.current and self.number == number:
            return None
            
        self.set_label( "Page : %d/%d" % (self.current + 1, 1 + number/self.max_tiles))
        
        buttons_text = []
        buttons_callback = []
        if self.current > 0:
            buttons_text.append( "Previous" )
            buttons_callback.append(self.app.previous_page)
        if self.current < int(float(number)/float(self.max_tiles)):
            buttons_text.append( "Next" )
            buttons_callback.append(self.app.next_page)
        
        self.set_buttons( buttons_text, buttons_callback)
            
        self.current = self.app.current
        self.number = number

    def refresh(self):
        self.set_pagination( self.number )
        
DEFAULT_ALBUM_DATA = Image.open("album_default.png")
DEFAULT_FILE_DATA = Image.open("file_default.png")

class Tile(Panel):
    def __init__(self, app, master, *args, **kwargs):
        super().__init__(master, width=THUMBNAIL_WIDTH+BORDER_THUMB, 
        height=THUMBNAIL_HEIGHT+BORDER_THUMB, bg="white", *args, **kwargs)
        
        self.app = app
        
        self.obj = None
        self.version = 0
        self.selected = False
        self.data = None
        
        self.thumbnail = Canvas(self, bg="white", width=THUMBNAIL_WIDTH, height=THUMBNAIL_HEIGHT)
        self.thumbnail.pack()
        self.title = Label(self)
        self.title.pack()
    
    def show(self):
        #self.grid(row=self.i, column=self.j)
        if self.obj :
            self.thumbnail.pack()
            if isinstance(self.obj, Album):
                self.title.pack()
    
    def hide(self):
        self.configure(bg="white")
        self.title.pack_forget()
        self.thumbnail.pack_forget()
    
    def set_album(self, album):  
        if album.cover :
            self.data = ImageTk.PhotoImage(Image.open( album.cover ))
        else:
            self.data = ImageTk.PhotoImage(DEFAULT_ALBUM_DATA)
            
        def _display(event):
            self.app.parents_album.append(album)
            self.app.action = Action.pagination
            self.app.refresh()
        
        self.title.configure(text=album.name)
        
        return _display, lambda event : self.app.select( album )
            
    def set_file(self, _file):  
        self.title.pack_forget()
        
        if _file.metadata.thumbnail :
            self.data = ImageTk.PhotoImage(Image.open( _file.metadata.thumbnail ))
        else:
            self.data = ImageTk.PhotoImage(DEFAULT_FILE_DATA)
      
        return lambda event: self.app.display_file( _file ), lambda event: self.app.select( _file )
        
    def refresh(self):
        self.set(self.obj)
        
    def set(self, obj):
        if self.selected != (obj in self.app.selected):
            self.configure(bg="blue" if obj in self.app.selected else "white")
            self.selected = obj in self.app.selected
        
        if self.obj == obj and self.version == obj.version() :
            return None
        
        if isinstance(obj, Album):
            callback1, callback2 = self.set_album(obj)
        else:
            callback1, callback2 = self.set_file(obj)
        
        self.obj = obj
        self.version = obj.version()
            
        self.thumbnail.delete("all")
        self.thumbnail.create_image(0, 0, anchor=NW, image=self.data) 
        self.thumbnail.bind('<Double-Button-1>', callback1 ) 
        self.thumbnail.bind('<Triple-Button-1>', callback1 ) 
        self.thumbnail.bind('<Button-3>', callback1 ) 
        self.thumbnail.bind('<Button-1>', callback2 ) 
    
        self.thumbnail.pack(padx=BORDER_THUMB/2, pady = BORDER_THUMB/2)
        
class PaginationPanel(VScrolledPanel):
    def __init__(self, app, master, num_x, num_y, *args, **kwargs):
        super().__init__(master, bg="white", *args, **kwargs)
        
        self.num_x = num_x
        self.num_y = num_y
        
        self.last_len = 0
        
        self.tiles=[ Tile(app, self.interior) for j in range(num_x*num_y) ]
        for j in range(num_y):
            for i in range(num_x):
                self.tiles[i * num_y + j].grid(row=i, column=j)
                self.tiles[i * num_y + j].i=i
                self.tiles[i * num_y + j].j=j
         
        self.sort_functions={
            "name":{
                Album: (lambda album : album.name),
                File : (lambda _file : _file.filename)
            },"date":{
                Album: (lambda album : album.datetime),
                File: (lambda _file : _file.metadata.datetime)
            },"size":{
                Album: (lambda album : len(album) ),
                File: (lambda _file : _file.metadata.size)
            }
        }
         
    def refresh(self):
        for i in range(self.last_len):
            self.tiles[i].refresh()
                
    def set(self, objs, sortname="name"):        
        if objs:
            tmp = objs.pop()
            objs.add( tmp )
            objs = sorted( objs, key=self.sort_functions[sortname][type(tmp)])
            #objs.sort( key=self.sort_functions[sortname][type(objs[0])] )
        self.reset()

        print("objs len %d"% len(objs))
        for i in range(0, min(len(objs), len(self.tiles))):
            self.tiles[i].set( objs[i] )
            self.tiles[i].show()
            
            
        
        for i in range(len(objs), len(self.tiles)):
            self.tiles[i].hide()
        
        self.last_len = min( len(objs), len(self.tiles))

class DisplayPanel(Panel):
    def __init__(self, app, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        
        self.data = None
        self.obj = None
        self.version = 0
        
        self.thumbnail = Canvas(self, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
        self.thumbnail.bind('<Escape>', lambda event: app.back ) 
        self.thumbnail.pack()
     
    def refresh(self):
        None
        
    def set(self, obj):
        if self.obj == obj and self.version == obj.version() :
            return None
                
        self.obj = obj
        self.version = obj.version()
            
        im=Image.open( obj.location )
        
        width, height = im.size
        ratio = float(width)/float(height)
        if float(width)/float(DISPLAY_WIDTH) < float(height)/float(DISPLAY_HEIGHT):
            height = min(height,DISPLAY_HEIGHT)
            width = int(ratio * height)
        else:
            width = min(width,DISPLAY_HEIGHT)
            height = int(width / ratio)

        self.data = ImageTk.PhotoImage(im.resize((width, height), Image.ANTIALIAS))
        self.thumbnail.delete("all")
        self.thumbnail.create_image(0, 0, anchor=NW, image=self.data) 
            
class MainPanel(Panel):
    def __init__(self, app, master, num_x=6, num_y=6, max_buttons=5, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        
        self.topPanel = TopPanel(app, self, max_buttons)
        self.topPanel.grid(row=0, column=0)
        
        self.bottomPanel = PaginationBottomPanel(app, self, max_buttons, num_x*num_y)
        self.bottomPanel.grid(row=0, column=2)
        
        self.centers = {
            "pagination" : PaginationPanel(app, self, num_x, num_y),
            "display" : DisplayPanel(app, self)
        }
        
        for panel in self.centers.values() :
            panel.grid(row=0, column=1)
            panel.hide()
            
        self.centerPanel = self.centers["pagination"]
        self.centerPanel.show()
    
    def set_pagination(self, objs):
        self.bottomPanel.set_pagination(len(objs))
        
        if self.centerPanel != self.centers["pagination"]:
            self.centerPanel.hide()
            
        self.centerPanel = self.centers["pagination"]
        self.centerPanel.set(objs)
        self.centerPanel.show()
        
        self.topPanel.set_pagination()
        self.topPanel.show()
        
        self.bottomPanel.show()
        
    def set_display(self, obj):
        if self.centerPanel != self.centers["display"]:
            self.centerPanel.hide()
            
        self.centerPanel = self.centers["display"]
        self.centerPanel.set(obj)
        self.centerPanel.show()
        
        self.topPanel.set_display()
        self.topPanel.show()
        
        self.bottomPanel.hide()
    
    def refresh(self):
        self.centerPanel.refresh()
        self.topPanel.refresh()
        self.bottomPanel.refresh()
