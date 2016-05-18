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

exts   = [ "png", "jpeg", "jpg", "mov", "mp4", "mpg", "thm", "3gp"]
img_exts = [ "png", "jpeg", "jpg"]
mv_exts = ["mov", "mp4", "mpg", "thm", "3gp"]

def check_ext(filename, exts_=exts):
    currentExt  = filename.split( '.' )[ -1 ]
    return currentExt.lower() in exts_
