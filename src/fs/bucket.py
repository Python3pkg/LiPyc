from lipyc.crypto import AESCipher
import os
import lipyc.crypto 
import shutil
from time import time
from threading import Lock
from ftplib import FTP, FTP_TLS
from tempfile import SpooledTemporaryFile

from lipyc.fs.utility import *
from lipyc.fs.container import Container
from lipyc.fs.transaction import Transaction
from urllib.parse import urlparse

class Bucket(Container): #décrit un dossier ex: photo, gdrive, dropbox
    def make(lib_name, name, json_bucket, aeskey):
        b = Bucket(
            lib_name = lib_name,
            path=json_bucket["path"], 
            max_capacity=json_bucket["max_capacity"],
            speed=json_bucket["speed"],
            name=name,
            crypt=json_bucket["crypt"],
            aeskey=json_bucket["aeskey"] if "aeskey" in json_bucket else aeskey,
            login=json_bucket["login"] if "login" in json_bucket else '',
            pwd=json_bucket["pwd"] if "pwd" in json_bucket else '')
        
        if 'free_capacity' in json_bucket:
            free_capacity = json_bucket['free_capacity']
        return b
            
    def __init__(self, lib_name, max_capacity=0, path="", speed=1.0, name="", 
    crypt=False, aeskey="", login='', pwd=''):
        super().__init__(name, max_capacity, speed)
        self.lib_name = lib_name
        self.crypt = crypt
        self.aeskey = aeskey
        self.path = path
                
        self.previous_lock = ''
                
        self.lock = Lock()
        self._id =  generate_id(name)
        
        self.urlObj = urlparse( path )
        self.scheme = self.urlObj.scheme #if not self.scheme ie mounted in user space
        self.login  = login
        self.pwd    = pwd
        
        
        dirs = ["data", "locks", "metadata", "transactions"]
        if not self.scheme: 
            for d in dirs:
                tmp = os.path.join(path, d)
                if not os.path.isdir(tmp):
                    os.mkdir(tmp)
        elif self.scheme[:3]=='ftp':
            with self.connect_ftp() as ftp:
                for d in dirs:
                    ftp.mkd(self.urlObj.path+'/'+d if self.urlObj.path else d)
       
    def reset_storage(self): #ftp ready
        dirs = ["data", "locks", "metadata", "transactions"] 
        for d in dirs:
            if not self.scheme:
                shutil.rmtree(os.path.join(self.path, d))
            elif self.scheme[:3]=='ftp':
                with self.connect_ftp() as ftp:
                    ftp.rmd(self.urlObj+'/'+d)
                    
    def access(self, key):
        return self
       
    def place(self, key, size):
        return self
        
    def buckets(self):
        return [self]
        
    def write(self, md5, size, fp):#ftp ready
        with self.lock:
            self.free_capacity -= size
            if self.crypt :
                self.free_capacity -= 2*lipyc.crypto.BS
            assert(self.free_capacity >= 0)
        
        if not fp :
            return 
            
        last = fp.tell()
        fp.seek(0)
        
        if not self.scheme:
            if self.crypt :
                cipher = AESCipher(self.aeskey)
                with open(make_path(self.path, self.lib_name, md5), "wb") as fp2:
                    cipher.encrypt_file( fp, fp2)
            else:
                with open(make_path(self.path, self.lib_name, md5), "wb") as fp2:
                    shutil.copyfileobj(fp, fp2)
        elif self.scheme[:3]=='ftp':
            if self.crypt :
                cipher = AESCipher(self.aeskey)
                fp2 = pooledTemporaryFile(10*1024*1024)
                cipher.encrypt_file( fp, fp2)
                fp2.seek(0)
            else:
                fp2 = fp
                
            ftp = self.connect_ftp()
            ftp.storbinary('STOR '+make_path(self.urlObj.path, self.lib_name, md5), fp2)
            
            if self.crypt :
                fp2.close()
        fp.seek(last)
    
    def connect_ftp(self):
        ftp = FTP() if self.scheme[-1]=='s' else FTP_TLS()
        ftp.connect(self.urlObj.netloc)
        ftp.login(self.login, self.pwd)
        return ftp
    
    def remove(self, md5, size):#ftp ready
        with self.lock:
            self.free_capacity += size 
            assert(self.free_capacity <= self.max_capacity)
            
        if not self.scheme:
            os.remove( make_path(self.path, self.lib_name, md5) )
        elif self.scheme[:3]=='ftp':
            ftp = self.connect_ftp()
            ftp.delete( make_path(self.urlObj.path, self.lib_name, md5) )
            
    def get_file(self, md5):#ftp ready
        if not self.scheme:
            if not self.crypt:
                return open( make_path(self.path, self.lib_name, md5), "rb")
            else:
                cipher = AESCipher(self.aeskey)
                fp2 = tempfile.TemporaryFile(10*1024*1024,mode="r+b")
                with open(make_path(self.path, self.lib_name, md5), "rb") as fp:
                    cipher.decrypt_file( fp, fp2)

                return fp2        
        elif self.scheme[:3]=='ftp':
            ftp = self.connect_ftp()
            
            fp = tempfile.TemporaryFile(10*1024*1024,mode="r+b")
            ftp.retrbinary('RETR '+make_path(self.urlObj.path, self.lib_name, md5), 
            fp.write)
            fp.seek(0)
            
            if not self.crypt:
                return fp
            else:
                cipher = AESCipher(self.aeskey)
                fp2 = tempfile.TemporaryFile(10*1024*1024,mode="r+b")
                cipher.decrypt_file( fp, fp2)
                fp.close()
                return fp2
                
    def __getstate__(self):
        state = super().__getstate__()
        state["lib_name"] = self.lib_name
        state["path"] = self.path
        state["crypt"] = self.crypt
        state["aeskey"] = self.aeskey
        state["urlObj"] = self.urlObj
        state["scheme"] = self.scheme
        state["login"] = self.login
        state["pwd"] = self.pwd
        state["previous_lock"] = self.previous_lock
        return state
        
    def __setstate__(self, state):
        super().__setstate__(state)
        self.lib_name = state['lib_name']
        self.path = state['path']
        self.crypt = state['crypt']
        self.aeskey = state['aeskey']
        self.urlObj = state['urlObj']
        self.scheme = state['scheme']
        self.login = state['login']
        self.pwd = state['pwd']
        self.previous_lock = state['previous_lock']

        self.lock=Lock()
        
    def try_lock(self, idclient, ttl):#ftp ready
        if not self.scheme:
            onlyfiles = [f for f in os.listdir(os.path.join(self.path, "locks")) if os.path.isfile(os.path.join(self.path, f))]
        elif self.scheme[:3]=='ftp':
            with self.ftp_connect() as ftp:
                onlyfiles = filter(lambda x,y:y['type'] == 'file', ftp.mlsd(self.urlObj.path+'/'+'locks', ['type']))
                
        for f in onlyfiles:
            if int(f.split("-")[3]) + ttl > time():
                return False
                
        self.previous_lock = "lock_%s_%d_%d" % (self.lib_name, idclient, time())
        
        if not self.scheme:
            fp = open( os.path.join(self.path, "locks", self.previous_lock), 'w')
            fp.write('0')
        elif self.scheme[:3]=='ftp':
            ftp.storbinary('STOR '+self.urlObj.path + '/' + 'locks' + '/' + self.previous_lock, None)
        return True
        
    def is_locked(self, idclient, ttl):#ftp ready
        if not self.scheme:
            onlyfiles = [f for f in os.listdir(os.path.join(self.path, "locks")) if os.path.isfile(os.path.join(self.path, f))]
        elif self.scheme[:3]=='ftp':
            with self.ftp_connect() as ftp:
                onlyfiles = filter(lambda x,y:y['type'] == 'file', ftp.mlsd(self.urlObj.path+'/'+'locks', ['type']))
                
        onlyfiles.filter(lambda f:f.split('-')[1]==self.lib_name)
        onlyfiles = sorted(onlyfiles, keys=lambda x: int(x.split('-')[3]), reverse=True)
        
        if not onlyfiles:
            return False
        
        if int(f.split("-")[3]) + ttl < time() or f.split("-")[2] != idclient:
            return False
        else:
            True
        
    
    def unlock(self):#ftp ready
        if not self.previous_lock:
            return
        
        if not self.scheme:
            if os.path.exists(os.path.join(self.path, "locks", self.previous_lock)):
                os.remove(os.path.join(self.path, "locks", self.previous_lock))
        elif self.scheme[:3]=='ftp':
            with self.ftp_connect() as ftp:
                onlyfiles = filter(lambda x,y:y['type'] == 'file', ftp.mlsd(self.urlObj.path+'/'+'locks', ['type']))
                if self.previous_lock in map(lambda x,y:x, onlyfiles):
                    ftp.delete(self.urlObj.path+'/'+'locks'+'/'+self.previous_lock)

        self.previous_lock = ''
        
    def transactions(self):#ftp ready
        transactions = set()

        if not self.scheme:
            for path, dirs, files in os.walk(os.path.join(self.path, 'transactions')): #rewirte with scandir for 3.5
                for filename in files:
                    location = os.path.join(path, filename)
                    
                    id_lib, id_client, _ = filename.split('-')
                    if(id_lib == self.lib_name):
                        tmp = Transaction(id_client, id_lib)
                        tmp.load(os.path.join(path, filename))
                        transactions.add( tmp )
        elif self.scheme[:3]=='ftp':
            with self.ftp_connect() as ftp:
                onlyfiles = filter(lambda x,y:y['type'] == 'file', ftp.mlsd(self.urlObj.path+'/'+'transactions', ['type']))
                for filename in onlyfiles:
                    location = os.path.join(path, filename)
                    
                    id_lib, id_client, _ = filename.split('-')
                    if(id_lib == self.lib_name):
                        tmp = Transaction(id_client, id_lib)
                        tmp.load(os.path.join(path, filename))
                        transactions.add( tmp )
        return transactions
