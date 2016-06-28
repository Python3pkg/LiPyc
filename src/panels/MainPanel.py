from tkinter import * 
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText

from PIL import Image
from PIL import ImageTk# https://pillow.readthedocs.io/en/3.2.x/   libjpeg-dev sudo pip3 install pillow  sudo apt-get install libjpeg8-dev python3-pil.imagetk
from PIL.ExifTags import TAGS
from tkinter import ttk

import os.path
import pickle
import hashlib
import time
import shutil
import random
import logging
import copy
import threading
from lipyc.scheduler import *
from math import ceil
from enum import Enum
import copy
from timeit import default_timer

from lipyc.panels.Panel import Panel, VScrolledPanel
from lipyc.Album import Album
from lipyc.File import File
from lipyc.config import *
from lipyc.scheduler import scheduler


sort_functions={
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

sort_functions_names = sorted( sort_functions )



class TopPanel(Panel):
    def __init__(self, app, master, max_buttons, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        
        self.app = app
        
        self.buttons = []
        self.buttons_text = ["" for k in range(max_buttons)]
        self.buttons_callback = [None for k in range(max_buttons)]
            
        self.last_action = ""
        self.last_parents = 0
        self.last_k = -1

        
        for k in range(max_buttons):
            tmp = ttk.Frame(self)
            tmp.button = ttk.Button(tmp)
            tmp.widget = None
            tmp.button.pack(side=RIGHT)
            
            tmp.grid(row=k, column=max_buttons)
            tmp.grid_forget()
                        
            self.buttons.append(tmp)
        
        self.current_pagination = -1
        self.number = -1
    def set_buttons(self, texts, callbacks ):
        if self.buttons_text == texts and self.buttons_callback == callbacks:
            return None
        
        for k in range(0, min(len(texts), len(self.buttons))):
            self.buttons[k].button.configure( text=texts[k], command=callbacks[k] )
            self.grid()
            
            self.buttons[k].grid(row=0, column=k)
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
            if callback:
                callback()
        
            self.buttons[k].widget.destroy()
            self.last_action = "" #redraw foced
            self.app.refresh()
            
        self.buttons[k].widget = make( self.buttons[k] )
        self.buttons[k].widget.pack()
        self.buttons[k].button.configure( text=text, command=reset_ )
        
        self.buttons_text[k] = text
        self.buttons_callback[k] = callback
       
    def set_pagination(self):    
        if self.last_action == "pagination" and self.last_parents == len(self.app.parents_album):
            return None

        self.last_action = "pagination"
        self.last_parents = len(self.app.parents_album)
        
        texts=["Back"] if self.app.parents_album else []
        texts.extend([
            "Add album",
            "Show files",
            "Show albums",
            "Sort by",
        ])
        
        callbacks=[self.app.back] if self.app.parents_album else []

        def sort_(master):
            frame = Frame(master)
            self.listBox =  Listbox(frame, selectmode=BROWSE, height=2)
            scrollBar = Scrollbar(frame, command = self.listBox.yview)
            self.listBox.config(yscrollcommand = scrollBar.set) 
           
            for name in sort_functions_names:
                self.listBox.insert("end", name)
                
            self.listBox.pack(side = LEFT, fill = Y) 
            scrollBar.pack(side = RIGHT, fill = Y)    
            return frame
            
        
        offset = len(callbacks)
        name = StringVar() 
        name.set("New_name")
        callbacks.extend([
            lambda _=None : self.set_widget_for(offset, lambda master:Entry(master, textvariable=name, width=15), "Add", lambda _=None:self.app.add_album(name.get())),
            self.app.show_files,
            self.app.show_albums,
            lambda _=None : self.set_widget_for(offset+3, lambda master:sort_(master), "Sort", lambda _=None:self.app.set_sortname(self.listBox.get(self.listBox.curselection()))),
        ])
        
        self.set_buttons( texts, callbacks)

    def set_display(self):     
        if self.last_action == "display":
            return None
        self.last_action = "display"
           
        texts=["Back", "Previous","Next"]
        callbacks=[self.app.back, 
        self.app.display_previous, 
        self.app.display_next]
        
        self.set_buttons( texts, callbacks)
    
    def set_similarities(self, number):
        if self.last_action == "similarities" and self.current_pagination == self.app.current_pagination and self.number == number:
            return None
        
        self.current_pagination = self.app.current_pagination
        self.number = number
        self.last_action = "similarities"

        buttons_text = ["Back"]
        buttons_callback = [self.app.back]
        if self.current_pagination > 0:
            buttons_text.append( "Previous" )
            buttons_callback.append(self.app.previous_pagination)
        if self.current_pagination < self.number-1:
            buttons_text.append( "Next" )
            buttons_callback.append(self.app.next_pagination)
        self.set_buttons(buttons_text, buttons_callback)
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
            tmp.grid(row=0, column=k+1)
            tmp.grid_forget()
            
            self.buttons.append(tmp)
            
        self.number = -1
        self.current = -1
            
    def set_label(self, text):
        self.label.configure(text=text)
        self.label.grid()
    
    def set_buttons(self, texts, callbacks ):
        if self.buttons_text == texts and self.buttons_callback == callbacks:
            return None
        
        for k in range(0, min(len(texts), len(self.buttons))):
            print(texts[k])
            self.buttons[k].configure( text=texts[k], command=callbacks[k] )
            self.buttons[k].grid(row=0, column=k+1)
            
            self.buttons_text[k] = texts[k]
            self.buttons_callback[k] = callbacks[k]
        
        for k in range(len(texts), len(self.buttons)):
            self.buttons[k].grid_forget()
            self.buttons_text[k] = ""
            self.buttons_callback[k] = None
    
    def set_pagination(self, number):
        if self.current == self.app.current and self.number == number:
            return None
            
        self.current = self.app.current
        self.number = number
        
        self.set_label( "Page : %d/%d" % (self.current + 1, ceil(float(number)/self.max_tiles)))
        
        buttons_text = []
        buttons_callback = []
        if self.current > 0:
            buttons_text.append( "Previous" )
            buttons_callback.append(self.app.previous_page)
        if self.current+1 < int(number/self.max_tiles):
            buttons_text.append( "Next" )
            buttons_callback.append(self.app.next_page)
        
        self.set_buttons( buttons_text, buttons_callback)

    def refresh(self):
        self.set_pagination( self.number )

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
        if self.obj :
            self.thumbnail.pack(padx=BORDER_THUMB/2, pady = BORDER_THUMB/2)
            if isinstance(self.obj, Album):
                self.title.pack()
    
    def hide(self):
        self.configure(bg="white")
        self.title.pack_forget()
        self.thumbnail.pack_forget()
    
    def set_album(self, album, k):  
        def _display(event):
            self.app.parents_album.append(album)
            self.app.action = Action.pagination
            self.app.refresh()
        
        self.title.configure(text=album.name)
        self.title.pack()
        
        return _display, lambda event : self.app.select( album, k )
            
    def set_file(self, _file, k): 
        self.title.pack_forget()
        
        def callback1(event):
            if self.app.parents_album:
                self.app.parents_album.append( self.app.parents_album[-1] )
            self.app.display_file( _file, k )
        return callback1, lambda event: self.app.select( _file, k )
        
    def refresh(self):
        self.set(self.obj)
        
    def set(self, obj, k):
        if self.selected != (obj in self.app.selected):
            self.configure(bg="blue" if obj in self.app.selected else "white")
            self.selected = obj in self.app.selected
            self.show()
        
        if self.obj == obj and self.version == obj.version() :
            return None
        
        if obj.thumbnail in thumbnails_cache:
            self.data = thumbnails_cache[obj.thumbnail]
        else:
            self.data = ImageTk.PhotoImage( Image.open(scheduler.get_file( obj.thumbnail ) ))
            thumbnails_cache[obj.thumbnail] = self.data
        
        if isinstance(obj, Album):
            callback1, callback2 = self.set_album(obj, k)
        else:
            callback1, callback2 = self.set_file(obj, k)
        
        self.obj = obj
        self.version = obj.version()

        offset_width = (THUMBNAIL_WIDTH - self.data.width()) / 2
        offset_height = (THUMBNAIL_HEIGHT- self.data.height()) / 2
            
        self.thumbnail.delete("all")
        self.thumbnail.create_image(offset_width, offset_height, anchor=NW, image=self.data) 
        self.thumbnail.bind('<Double-Button-1>', callback1 ) 
        self.thumbnail.bind('<Triple-Button-1>', callback1 ) 
        self.thumbnail.bind('<Button-3>', callback1 ) 
        self.thumbnail.bind('<Button-1>', callback2 ) 
    
        self.thumbnail.pack(padx=BORDER_THUMB/2, pady = BORDER_THUMB/2)
        
class PaginationPanel(VScrolledPanel):
    def __init__(self, app, master, num_x, num_y, *args, **kwargs):
        super().__init__(master, bg="white", *args, **kwargs)
        self.canvas.configure(height=480)
        
        self.app = app
        self.num_x = num_x
        self.num_y = num_y
        
        self.last_len = 0
        self.sortname = "name"
        
        self.tiles=[ Tile(app, self.interior) for j in range(num_x*num_y) ]
        for j in range(num_y):
            for i in range(num_x):
                self.tiles[i * num_y + j].grid(row=i, column=j)
                self.tiles[i * num_y + j].i=i
                self.tiles[i * num_y + j].j=j
         
    def refresh(self):
        for i in range(self.last_len):
            self.tiles[i].refresh()
                
    def set_sortname(self, name):
        self.sortname = name
            
    def set(self, objs):        
        if objs:
            tmp = objs.pop()
            objs.add( tmp )
            objs = list(sorted( objs, key=sort_functions[self.app.sortname][type(tmp)]))[self.app.current*self.num_x*self.num_y:]
            self.app.set_last_objs(self.app.current_pagination, objs)

        for i in range(0, min(len(objs), len(self.tiles))):
            self.tiles[i].set( objs[i], i )
            self.tiles[i].show()
            
            
        
        for i in range(len(objs), len(self.tiles)):
            self.tiles[i].hide()
        
        self.last_len = min( len(objs), len(self.tiles))

class SchedulerPanel(Panel):
    def __init__(self, app, master, *args, **kwargs):
        super().__init__(master, bg="white", *args, **kwargs)
        
        self.app = app
        
        self.textarea = ScrolledText(self)
        self.textarea.pack()
        
        self.b_frame = Frame(self)
        self.b_frame.pack()
        
        self.b_save = Button(self.b_frame, text="Save", command=lambda _=None:self.app.save_pgs(self.textarea.get("1.0",END)))
        self.b_save.pack(side=LEFT)
        self.b_leave = Button(self.b_frame, text="Leave", command=self.app.show_library)
        self.b_leave.pack(side=LEFT)
    
    def refresh(self):
        pass
            
    def reset(self):
        pass
            
    def set(self):  
        self.textarea.delete("1.0", END)

        if os.path.isfile("pgs.json"):
            location = "pgs.json"
        else:
            location = location_pgs_default
            
        with open(location, "r") as fp:    
            self.textarea.insert(END, fp.read())      
        
class EasySchedulerPanel(Panel):
    def __init__(self, app, master, *args, **kwargs):
        super().__init__(master, bg="white", *args, **kwargs)
        
        self.app = app
        self.memory = {}
        
        
        self.f_buttons = Frame(self)
        self.f_buttons.pack()
        self.b_apply = Button(self.f_buttons, text="Apply", 
            command=lambda _=None:scheduler.update_structure( self.v_replicat.get(),
            [value for key,value in self.memory.items() if len(key.split('|')) ==1 and key !='']) )
        self.b_apply.pack(side=LEFT)
        self.b_reset = Button(self.f_buttons, text="Reset", command=self.reset_all)
        self.b_reset.pack(side=LEFT)
        
        
        self.f_general = Frame(self)
        
        self.v_max_ratio = IntVar()
        global max_ratio
        self.v_max_ratio.set( max_ratio )
        self.e_max_ratio = Entry(self.f_general, textvariable=self.v_max_ratio)
        self.l_max_ratio = Label(self.f_general, text="max_ratio")
        self.l_max_ratio.grid(row=0, column=0)
        self.e_max_ratio.grid(row=0, column=1)
        
        self.v_replicat = IntVar()
        self.v_replicat.set( scheduler.replicat )
        self.e_replicat = Entry(self.f_general, textvariable=self.v_replicat)
        self.l_replicat = Label(self.f_general, text="replicat")
        self.l_replicat.grid(row=1, column=0)
        self.e_replicat.grid(row=1, column=1)
        
        self.f_general.pack()
        
        
        ####
        self.f_pgs = Frame(self)
        self.f_pgs.pack()
        self.tree = ttk.Treeview(self.f_pgs, columns=('aeskey', 'crypt', 
        'max_capacity', 'speed', 'path'))
        self.tree.heading('aeskey', text='AESkey')
        self.tree.heading('crypt', text='Crypt')
        self.tree.heading('max_capacity', text='Capacity')
        self.tree.heading('speed', text='Speed')
        self.tree.heading('path', text='Path')

        self.tree.grid(row=0, column=0)
        self.tree.grid(row=0, column=0)
        
        self.ysb = ttk.Scrollbar(self.f_pgs, orient='vertical', command=self.tree.yview)
        self.xsb = ttk.Scrollbar(self.f_pgs, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscroll=self.ysb.set, xscroll=self.xsb.set)
        self.ysb.grid(row=0, column=1, sticky='ns')
        self.xsb.grid(row=1, column=0, sticky='ew')
        
        self.make_tree()
        
        self.f_pgs_buttons = Frame(self.f_pgs)
        self.f_pgs_buttons.grid(row=2, column=0)
        self.b_add = Button(self.f_pgs_buttons, text="Add", 
            command=lambda _=None:self.build_add(self.tree.focus()))
        self.b_add.pack(side=LEFT)
        self.b_remove = Button(self.f_pgs_buttons, text="Remove", 
            command=lambda _=None:self.app.build_)
        self.b_remove.pack(side=LEFT)
        self.b_update = Button(self.f_pgs_buttons, text="Update", 
            command=lambda _=None:self.build_update(self.tree.focus()))
        self.b_update.pack(side=LEFT)
        ###
        
        self.f_area = Frame(self)
        
        self.common_area = Frame(self.f_area)
        self.common_area.pack()
        self.l_area_name = Label(self.common_area, text="Name")
        self.l_area_name.grid(row=0, column=0)
        self.v_area_name = StringVar()
        self.e_area_name = Entry(self.common_area, textvariable=self.v_area_name)
        self.e_area_name.grid(row=0, column=1)
        
        self.bucket_area = Frame(self.f_area)
        self.bucket_area.pack()
        self._bucket_area = Frame(self.bucket_area)
        self.l_area_aeskey = Label(self._bucket_area, text="AESKey")
        self.l_area_aeskey.grid(row=1, column=0)
        self.v_area_aeskey = StringVar()
        self.e_area_aeskey = Entry(self._bucket_area, textvariable=self.v_area_aeskey)
        self.e_area_aeskey.grid(row=1, column=1)
        
        self.l_area_crypt = Label(self._bucket_area, text="Crypt?")
        self.l_area_crypt.grid(row=2, column=0)
        self.v_area_crypt = BooleanVar()
        self.e_area_crypt = Entry(self._bucket_area, textvariable=self.v_area_crypt)
        self.e_area_crypt.grid(row=2, column=1)
        
        self.l_area_max_capacity = Label(self._bucket_area, text="Capacity( Bytes)")
        self.l_area_max_capacity.grid(row=3, column=0)
        self.v_area_max_capacity = IntVar()
        self.e_area_max_capacity = Entry(self._bucket_area, textvariable=self.v_area_max_capacity)
        self.e_area_max_capacity.grid(row=3, column=1)
        
        self.l_area_speed = Label(self._bucket_area, text="Speed")
        self.l_area_speed.grid(row=4, column=0)
        self.v_area_speed = DoubleVar()
        self.e_area_speed = Entry(self._bucket_area, textvariable=self.v_area_speed)
        self.e_area_speed.grid(row=4, column=1)
        
        self.l_area_path = Label(self._bucket_area, text="Path")
        self.l_area_path.grid(row=5, column=0)
        self.v_area_path = StringVar()
        self.e_area_path = Entry(self._bucket_area, textvariable=self.v_area_path)
        self.e_area_path.grid(row=5, column=1)
 
        self.b_area_process = Button(self.f_area, text="Process")
        self.b_area_process.pack()
    
    def reset_all(self):
        self.tree.delete(*self.tree.get_children())
        self.f_area.pack_forget()
        
        global max_ratio
        self.v_max_ratio.set( max_ratio )
        self.v_replicat.set( scheduler.replicat )
        
        print(max_ratio)
        self.make_tree()
    
    def make_tree(self):
        self.memory[''] = None
        for pg in scheduler.pgs:
            self.tree.insert( "", 'end',  pg.name , text=pg.name)
            self.memory[ pg.name ] = copy.deepcopy(pg)
            for pool in pg.children:
                self.tree.insert( pg.name, 'end',  pool.name, 
                    text=pool.name.split('|')[-1])
                self.memory[ pool.name ] = copy.deepcopy(pool)
                for bucket in pool.children:
                    self.tree.insert( pool.name, 'end',  bucket.name ,
                        text=bucket.name.split('|')[-1],
                        values=[bucket.aeskey, bucket.crypt, 
                        bucket.max_capacity, bucket.speed, bucket.path])
                    self.memory[ bucket.name ] = copy.deepcopy(bucket)
            
    def build_add(self, parent_id):
        self.b_area_process.configure(command= lambda _=None:self.process_add(parent_ids))
        parent = self.memory[parent_id]
        if len(name.split('|')) == 3: #bucket
            self.v_area_aeskey.set("")
            self.v_area_crypt.set(False)
            self.v_area_max_capacity.set(0)
            self.v_area_speed.set(1.0)
            self.v_area_path.set("")
            
            self.f_area.pack()
            self._bucket_area.pack()
        else:
            self.f_area.pack()
            self._bucket_area.pack_forget()
   
    def build_update(self, current_id):
        self.b_area_process.configure(command= lambda _=None:self.process_update(current_id))
        current = self.memory[current_id]
        name = current.name

        self.v_area_name.set( name.split('|')[-1] )
        
        if len(name.split('|')) == 3: #bucket
            self.v_area_aeskey.set(current.aeskey)
            self.v_area_crypt.set(current.crypt)
            self.v_area_max_capacity.set(current.max_capacity)
            self.v_area_speed.set(current.speed)
            self.v_area_path.set(current.path)
            
            self.f_area.pack()
            self._bucket_area.pack()
        else:
            self.f_area.pack()
            self._bucket_area.pack_forget()
            
    def process_add(self, parent_id):
        parent_name = self.memory[parent_id].name
        name = parent_name+'|'+self.v_area_name.get() if parent_name else self.v_area_name.get()
        values=[]
        if not parent_name: #pg 
            self.memory[name] = PG(name)
        elif len(parent_name.split('|')) == 1: #pool
            self.memory[name] = Pool(name)
            self.memory[parent_name].add( self.memory[name] )
        else: #bucket
            self.memory[parent_name].add( self.memory[name] )
            self.memory[name]=Bucket(name=name, 
                aeskey=self.v_area_aeskey.get(),
                crypt=self.v_area_crypt.get(),
                max_capacity=self.v_area_max_capacity.get(),
                path=self.v_area_path.get(),
                speed=self.v_area_speed.get()
                )
        
            values = [self.v_area_aeskey.get(), self.v_area_crypt.get(),
            self.v_area_max_capacity.get(), self.v_area_speed.get(), 
            self.v_area_path.get()]
            
        self.tree.insert( parent_name, 'end',  name.split('|')[-1], 
            text=name, values=values)
        self.f_area.pack_forget()
           
    def process_update(self, current_id):
        previous_name = self.memory[ current_id ].name
        name = '|'.join( previous_name.split('|')[:-1] + [self.v_area_name.get()] )
        parent_id =  '|'.join( previous_name.split('|')[:-1])
        
        if len(previous_name.split('|')[:-1])==1: #pg 
            self.memory[current_id] = PG(name)
            self.tree.item( current_id, text=name.split('|')[-1])

        elif len(previous_name.split('|')) == 2: #pool
            self.memory[parent_id].remove( self.memory[current_id] )
            self.memory[current_id] = Pool(name)
            self.memory[parent_id].add( self.memory[current_id] )

            
            self.tree.item( current_id, text=name.split('|')[-1])
        else: #bucket
            self.memory[parent_id].remove( self.memory[current_id] )
            self.memory[current_id]=Bucket(name=name, 
                aeskey=self.v_area_aeskey.get(),
                crypt=self.v_area_crypt.get(),
                max_capacity=self.v_area_max_capacity.get(),
                path=self.v_area_path.get(),
                speed=self.v_area_speed.get()
                )
            self.memory[parent_id].add( self.memory[current_id] )
            
            
            self.tree.item( current_id, text=name.split('|')[-1])
            self.tree.set( current_id, 'aeskey', self.v_area_aeskey.get())
            self.tree.set( current_id, 'crypt', self.v_area_crypt.get())
            self.tree.set( current_id, 'max_capacity', self.v_area_max_capacity.get())
            self.tree.set( current_id, 'speed', self.v_area_speed.get())
            self.tree.set( current_id, 'path', self.v_area_path.get())
            self.f_area.pack_forget()
        
        self.f_area.pack_forget()

        
    def refresh(self):
        pass
            
    def reset(self):
        pass
            
    def set(self):  
        pass     
        

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
        pass
        
    def reset(self):
        pass
        
    def set(self, obj):
        if self.obj == obj and self.version == obj.version() :
            return None
                
        self.obj = obj
        self.version = obj.version()
            
            
        if obj.md5 in files_cache:
            offset_width, offset_height, self.data = files_cache[obj.thumbnail]
        else:
            im=Image.open( scheduler.get_file( obj.md5) )
            
            width, height = im.size
            ratio = float(width)/float(height)
            if float(width)/float(DISPLAY_WIDTH) < float(height)/float(DISPLAY_HEIGHT):
                height = min(height, DISPLAY_HEIGHT)
                width = int(ratio * height)
            else:
                width = min(width, DISPLAY_WIDTH)
                height = int(width / ratio)
            
            
            offset_width = (DISPLAY_WIDTH - width) / 2
            offset_height = (DISPLAY_HEIGHT- height) / 2
                
            self.data = ImageTk.PhotoImage(im.resize((width, height), Image.ANTIALIAS))
            files_cache[obj.thumbnail] = (offset_width, offset_height, self.data)
            
        self.thumbnail.delete("all")
        self.thumbnail.create_image(offset_width, offset_height, anchor=NW, image=self.data) 
            
class MainPanel(Panel):
    def __init__(self, app, master, num_x=6, num_y=6, max_buttons=5, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        
        self.app = app
        
        self.num_x = num_x
        self.num_y = num_y
        
        self.topPanel = TopPanel(app, self, max_buttons)
        self.topPanel.grid(row=0, column=0)
        
        self.centers = {
            "pagination" : PaginationPanel(app, self, num_x, num_y, height=500),
            "display" : DisplayPanel(app, self),
            "scheduler": SchedulerPanel(app, self),
            "easy_scheduler": EasySchedulerPanel(app, self),
        }
        
        for panel in self.centers.values() :
            panel.grid(row=1, column=0)
            panel.hide()
            
        self.centerPanel = self.centers["pagination"]
        self.centerPanel.show()
        
        self.bottomPanel = PaginationBottomPanel(app, self, max_buttons, num_x*num_y)
        self.bottomPanel.grid(row=2, column=0)
    
    def set_pagination(self, objs):        
        if self.centerPanel != self.centers["pagination"]:
            self.centerPanel.hide()
        
        self.topPanel.set_pagination()
        self.topPanel.show()
        
        self.centerPanel = self.centers["pagination"]
        self.centerPanel.set(objs)
        self.centerPanel.show()
        
        self.bottomPanel.set_pagination(len(objs))
        self.bottomPanel.show()
        
    def set_display(self, obj):#k position app.last_objs
        if self.centerPanel != self.centers["display"]:
            self.centerPanel.hide()
            
        self.topPanel.set_display()
        self.topPanel.show()
            
        self.centerPanel = self.centers["display"]
        self.centerPanel.set(obj)
        self.centerPanel.show()
        
        self.bottomPanel.hide()
    
    def set_similarities(self, objs):                
        if self.centerPanel != self.centers["pagination"]:
            self.centerPanel.hide()
        
        self.topPanel.set_similarities(len(self.app.last_objs))
        self.topPanel.show()
        
        self.centerPanel = self.centers["pagination"]
        self.centerPanel.set(objs)
        self.centerPanel.show()
        
        self.bottomPanel.set_pagination(len(objs))
        self.bottomPanel.show()
      
    def set_scheduler(self):
        self.bottomPanel.hide()
        self.topPanel.hide()
        
        if self.centerPanel != self.centers["scheduler"]:
            self.centerPanel.hide()
        
        self.centerPanel = self.centers["scheduler"]
        self.centerPanel.set()
        self.centerPanel.show()
        
    def set_easy_scheduler(self):
        self.bottomPanel.hide()
        self.topPanel.hide()
        
        if self.centerPanel != self.centers["easy_scheduler"]:
            self.centerPanel.hide()
            
        self.centerPanel = self.centers["easy_scheduler"]
        self.centerPanel.set()
        self.centerPanel.show()
        
    def refresh(self):
        self.centerPanel.refresh()
        self.topPanel.refresh()
        self.bottomPanel.refresh()

    def reset(self):
        self.centerPanel.reset()
