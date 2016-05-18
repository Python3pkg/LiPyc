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

class TopMenu(Menu):
    def __init__(self, app, master, *args, **kwargs):
        Menu.__init__(self, master, *args, **kwargs)
        
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
        m_export.add_command(label="Export to", command= self.app.export_to)
        #m_export.add_command(label="Export lib to", command= self.app.export_lib_to)
        self.add_cascade(label="Export", menu=m_export)

