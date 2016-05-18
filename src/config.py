from enum import Enum


THUMBNAIL_HEIGHT = 128
THUMBNAIL_WIDTH = 128

DISPLAY_HEIGHT = 480
DISPLAY_WIDTH = 640

BORDER_THUMB = 4

class Action(Enum):
    pagination = 0 
    pagination_albums = 1
    pagination_files = 2
    display_file = 3
 
