import hashlib
import os

def wrand(seed, value):
    a, b = 6364136223846793005, 1
    
    return (a * ((a * seed + b) ^ value ) + b) % (2**32); 

def make_path(path, lib_name, md5):
    return os.path.join( path, "data", "%s-%s" % (lib_name, md5) ) 
  
def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def generate_id(name):
    return int( hashlib.md5(name.encode('utf-8')).hexdigest(), 16)
