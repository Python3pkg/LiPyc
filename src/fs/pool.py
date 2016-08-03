from lipyc.fs.container import Container
from lipyc.fs.bucket import Bucket

class Pool(Container):  #on décrit un disque par exemple avec pool
    def make(lib_name, name, json_pool, aeskey):#config json to pool
        pool = Pool(name)
        aeskey = json_pool["aeskey"] if "aeskey" in json_pool else ""
        if 'free_capacity' in json_pool:
            pool.free_capacity = json_pool['free_capacity']
        if 'max_capacity' in json_pool:
            pool.max_capacity = json_pool['max_capacity']
        
        for _name, json_pool in json_pool["buckets"].items():
            pool.add( Bucket.make(lib_name, name+"|"+_name, json_pool, aeskey) )
        
        return pool
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
