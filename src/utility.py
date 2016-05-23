from PIL import Image

from lipyc.config import *

def io_protect(default=None):
    def decorator(function):
        def new_function(self, *args, **kwargs):
            res = default
            with self.io_lock:
                res = function(self, *args, **kwargs)
            return res
        return new_function
    return decorator
    
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

def check_ext(filename, exts_=exts):
    currentExt  = filename.split( '.' )[ -1 ]
    return currentExt.lower() in exts_

def make_thumbnail(src, dst):
    im = Image.open( src )
    
    width, height = im.size
    ratio = float(width)/float(height)
    if float(width)/float(THUMBNAIL_WIDTH) < float(height)/float(THUMBNAIL_HEIGHT):
        height = min(height, THUMBNAIL_HEIGHT)
        width = int(ratio * height)
    else:
        width = min(width, THUMBNAIL_WIDTH)
        height = int(width / ratio)
            
    im.thumbnail( (width, height) )
    im.save(dst, "JPEG")
