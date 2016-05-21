#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-

from lipyc.Application import Application
from lipyc.Library import Library
from lipyc.Album import Album
from lipyc.File import File, FileMetadata
import sys
import logging

#logging.basicConfig(
        #stream= sys.stdout,
        #format='%(asctime)s  %(levelname)s  %(filename)s %(funcName)s %(lineno)d %(message)s',
        #level=logging.DEBUG)
logging.basicConfig(
        stream= sys.stdout,
        format='%(message)s',
        level=logging.DEBUG)

app = Application()
app.mainloop()