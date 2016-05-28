from tkinter import * 
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox

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

from lipyc.panels.Panel import Panel
from lipyc.File import File
from lipyc.Album import Album
from lipyc.config import *


class InfoPanel(Panel):
    def __init__(self, master, max_labels, max_buttons, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
                
        self.labels = []
        self.labels_text = ["" for k in range(max_labels)] #string list
        
        self.buttons = []
        self.buttons_text = ["" for k in range(max_buttons)]
        self.buttons_callback = [None for k in range(max_buttons)]
        
        for k in range(max_labels):
            tmp = Label(self)
            tmp.grid(row=k, column=0)
            tmp.grid_forget()
            
            self.labels.append(tmp)
            
        for k in range(max_buttons):
            tmp = Frame(self)
            tmp.button = Button(tmp)
            tmp.widget = None
            tmp.button.pack(side=RIGHT)
            
            tmp.grid(row=max_labels, column=k)
            tmp.grid_forget()
            
            self.buttons.append(tmp)
    
    def set_labels(self, texts ):
        if self.labels_text == texts:
            return None
            
        for k in range(0, min(len(texts), len(self.labels))):
            self.labels[k].configure( text=texts[k] )
            self.labels[k].grid()

            self.labels_text[k] = texts[k]
            
        for k in range(len(texts), len(self.labels)):
            self.labels[k].grid_forget()
            self.labels_text[k] = ""
    
    #
    #Be carfull with callback construction in order to ensure that semantique equivalence enforce physical equivalence
    #
    def set_buttons(self, texts, callbacks ):
        if self.buttons_text == texts and self.buttons_callback == callbacks:
            return None
        
        for k in range(0, min(len(texts), len(self.buttons))):
            if self.buttons[k].widget:
                self.buttons[k].widget.destroy()
                self.buttons[k].widget = None
            self.buttons[k].button.configure( text=texts[k], command=callbacks[k] )
            self.buttons[k].grid()
            
            self.buttons[k].grid(row=len(self.labels), column=k)
            self.buttons_text[k] = texts[k]
            self.buttons_callback[k] = callbacks[k]
        
        for k in range(len(texts), len(self.buttons)):
            self.buttons[k].grid_forget()
            self.buttons_text[k] = ""
            self.buttons_callback[k] = None
        
    def set_widget_for(self, k, make, text, callback): #befor button k, callback for button k
        if not self.buttons_callback[k]:
            return False
            
        def reset_():
            self.buttons[k].widget.destroy()
            if callback:
                callback()
            
        self.buttons[k].widget = make( self.buttons[k] )
        self.buttons[k].widget.pack()
        self.buttons[k].button.configure( text=text, command=reset_ )
        self.buttons_text[k] = text
        self.buttons_callback[k] = callback

class ActionPanel(Panel):
    def __init__(self, app, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        
        self.app = app
        
        self.tree = ttk.Treeview(self)
        self.tree.grid(row=0, column=0)
        self.tree.grid(row=0, column=0)
        
        self.ysb = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.xsb = ttk.Scrollbar(self, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscroll=self.ysb.set, xscroll=self.xsb.set)
        self.ysb.grid(row=0, column=1, sticky='ns')
        self.xsb.grid(row=1, column=0, sticky='ew')
        
        self.b_bar = Frame(self)
        self.b_bar.grid(row=2, column=0)
        self.b_addto = Button(self.b_bar, text="Add to", command = lambda _=None : self.app.add_to( self.map_albums[self.tree.focus()] if self.tree.focus() else None ))
        self.b_addto.grid(row=2, column=0)
        self.b_copyto = Button(self.b_bar, text="Copy to", command = lambda _=None : self.app.copy_to( self.map_albums[self.tree.focus()] if self.tree.focus() else None ))
        self.b_copyto.grid(row=2, column=1)
        self.b_copyto = Button(self.b_bar, text="Move to", command = lambda _=None : self.app.move_to( self.map_albums[self.tree.focus()] if self.tree.focus() else None ))
        self.b_copyto.grid(row=2, column=2)
        self.b_set_cover = Button(self.b_bar, text="Set cover", command =lambda _=None:None)
        #self.b_set_cover.grid(row=3, column=0)
        
        
        self.albums_map = {}
        self.map_albums = {}
        self.current = 0
   
    def make_tree(self):
        o = sorted(self.app.library.albums, key=lambda elt:elt.name)
        for elt in o:
            self.tree.insert( "", 'end',  str(self.current) ,text=elt.name)
                
            self.albums_map[ elt ] = str(self.current)
            self.map_albums[ str(self.current) ] = elt
            self.current += 1

        
        f = set()
        
        while o :
            tmp = o.pop()
            f.add(tmp)
            
            subalbums = sorted(tmp.subalbums, key=lambda elt:elt.name)
            o.extend( [album for album in subalbums if album not in f] )

            for elt in subalbums:
                self.tree.insert( self.albums_map[ tmp ], 'end',  str(self.current) ,text=elt.name)
                
                self.albums_map[ elt ] = str(self.current)
                self.map_albums[ str(self.current) ] = elt
                self.current += 1
    def set(self): #Must be called after each addition/removal/rename of an album
        self.tree.delete(*self.tree.get_children())
        self.make_tree()
            
        self.grid()
    
    def set_display(self, obj):
        self.b_set_cover.configure(command= lambda _=None : self.app.set_cover_from( self.map_albums[self.tree.focus()] if self.tree.focus() else None, obj ))
        self.b_set_cover.grid()
    
    def set_pagination(self, objs):
        if not objs:
            self.b_set_cover.grid_forget()
            return 
            
        obj = objs.pop()
        objs.add(obj)
        if len(objs) > 1:
            self.b_set_cover.grid_forget()
        elif isinstance(obj, File):
            self.b_set_cover.configure(command= lambda _=None : self.app.set_cover_from( self.map_albums[self.tree.focus()] if self.tree.focus() else None, obj ))
            self.b_set_cover.grid()
        else:
            self.b_set_cover.grid_forget()

    
class RightPanel(Panel):
    def __init__(self, app, master, *args, **kwargs):
        super().__init__(master, width=150, *args, **kwargs)
        
        self.app = app
        
        self.infoPanel = InfoPanel(self, 10, 10)
        self.actionPanel = ActionPanel(app, self)
        
        self.infoPanel.grid(row=0, column=0)
        self.infoPanel.hide()
        
        self.actionPanel.grid(row=1, column=0)
        self.actionPanel.hide()
        
        self.objs = None
        self.versions = None
        self.objs = None
        self.versions = None
    
    def set_display(self, obj):
        self.actionPanel.set_display(obj)
        self.actionPanel.show()
        
        if self.objs == [obj] and [obj.version()] == self.versions:
            return None
            
        self.infoPanel.set_labels([
            obj.filename,
            "Height : %d" % obj.metadata.height,
            "Width : %d" % obj.metadata.width,
            "Datetime : %s" % time.strftime( "%Y-%d-%m", obj.metadata.datetime)
        ])
        
        def _remove():
            self.app.remove_file(obj, True)
            self.app.back()
        self.infoPanel.set_buttons( ["Remove"], [_remove] )
        
        self.infoPanel.show()
        self.actionPanel.set_display(obj)
        self.actionPanel.show()
        
        self.objs = {obj}
        self.versions = [obj.version()]
    
    def set_pagination_unaire(self, obj):
        if isinstance(obj, File) :
            labels_texts= [
                obj.filename,
                "Height : %d" % obj.metadata.height,
                "Width : %d" % obj.metadata.width,
                "Datetime : %s" % time.strftime( "%Y-%d-%m", obj.metadata.datetime)
            ]
            buttons_texts = ["Remove"]
            callbacks = [
                lambda _=None : self.app.remove_file(obj, True)
            ]
        else:
            labels_texts= [
                obj.name,
                "Subalbums : %d" % len(obj.subalbums),
                "Files : %d" % len(obj.files),
                "Datetime : %s" % time.strftime( "%Y-%d-%m", obj.datetime)
            ]
            buttons_texts=["Set cover", "Rename", "Remove"]

            name = StringVar() 
            name.set(obj.name)
            callbacks = [ 
                lambda _=None : self.app.set_cover(obj),
                lambda _=None : self.infoPanel.set_widget_for(1, lambda master:Entry(master, textvariable=name, width=15), "Rename", lambda _=None:self.app.rename_album(obj, name.get())),
                lambda _=None : self.app.remove_album(obj, True)
            ]
        
        self.infoPanel.set_labels(labels_texts)
        self.infoPanel.set_buttons(buttons_texts, callbacks)
    
    def set_pagination_multpile(self, objs):
        labels_texts=[]
        a,f,n = 0,0, 0
        
        for obj in objs:
            if isinstance(obj, Album):
                a+=1
                n+=len(obj)
            else:
                f+=1
                n+=1
        
        self.infoPanel.set_labels([
            "Albums : %d" % a,
            "Files : %d" % f,
            "Rec files : %d" % n
        ])
        
        buttons_texts=["Remove"]
        callbacks = [ 
            lambda _=None : self.app.remove(objs)
        ]
        self.infoPanel.set_buttons(buttons_texts, callbacks)
    
    def set_pagination(self, objs):

        if self.objs == objs and [obj.version() for obj in objs] == self.versions :
            return None

        if objs :    
            if len(objs) == 1:
                self.set_pagination_unaire( list(objs)[0] )
            else:
                self.set_pagination_multpile( objs )
            
            self.infoPanel.show()
            
            self.actionPanel.set_pagination(objs)
            self.actionPanel.show()
        else:
            self.infoPanel.hide()
            self.actionPanel.hide()
            
        self.objs = copy.copy( objs )
        self.versions = [obj.version() for obj in objs]
