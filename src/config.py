from enum import Enum
from lipyc.Cache import ARCCache

import hashlib
import os
THUMBNAIL_HEIGHT = 128
THUMBNAIL_WIDTH = 128

DISPLAY_HEIGHT = 720
DISPLAY_WIDTH = 720

BORDER_THUMB = 4

class Action(Enum):
    pagination = 0 
    pagination_albums = 1
    pagination_files = 2
    display_file = 3
 
exts   = [ "png", "jpeg", "jpg", "mov", "mp4", "mpg", "thm", "3gp"]
img_exts = [ "png", "jpeg", "jpg"]
mv_exts = ["mov", "mp4", "mpg", "thm", "3gp"]


BUFFER_SIZE = 1<<21

hashlib.md5(open("album_default.png", "rb").read()).hexdigest()

thumbnails={
    "album":{
        "fp":"album_default.png", 
        "md5": hashlib.md5(open("album_default.png", "rb").read()).hexdigest(),
        "size":os.path.getsize("album_default.png")},
    "file":{
        "fp":"file_default.png", 
        "md5":hashlib.md5(open("file_default.png", "rb").read()).hexdigest(), 
        "size":os.path.getsize("file_default.png")}
}



thumbnails_cache = ARCCache( 100 )
files_cache = ARCCache( 20 )
