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
    pagination_similarities = 4
    configure_pgs = 5
    easy_configure_pgs = 6
 
exts   = [ "png", "jpeg", "jpg", "mov", "mp4", "mpg", "thm", "3gp"]
img_exts = [ "png", "jpeg", "jpg"]
mv_exts = ["mov", "mp4", "mpg", "thm", "3gp"]

from pkg_resources import resource_filename, resource_exists

location_album_default = resource_filename("lipyc.data", "album_default.png")
location_file_default = resource_filename("lipyc.data", "file_default.png")
location_pgs_default = resource_filename("lipyc.data", "default-pgs.json")

BUFFER_SIZE = 1<<21

hashlib.md5(open(location_album_default, "rb").read()).hexdigest()

thumbnails={
    "album":{
        "fp":location_album_default, 
        "md5": hashlib.md5(open(location_album_default, "rb").read()).hexdigest(),
        "size":os.path.getsize(location_album_default)},
    "file":{
        "fp":location_file_default, 
        "md5":hashlib.md5(open(location_file_default, "rb").read()).hexdigest(), 
        "size":os.path.getsize(location_file_default)}
}



thumbnails_cache = ARCCache( 100 )
files_cache = ARCCache( 20 )
