## @file 
# @author Laurent Prosperi
# @date June 2016
# @brief Not thread-safe( not the purpose)

import numpy as np
import json
from copy import copy
from lipyc.crypto import AESCipher
import itertools, functools
import os
import hashlib
import lipyc.crypto 
import logging
import shutil
import tempfile
import pickle
from threading import Lock, Condition
import collections
import sys
from time import time, sleep
from random import random
from collections import deque
from threading import Thread

from lipyc.fs.transaction import Transaction
from lipyc.fs.config import *

counter = 0

class InnerScheduler(Thread):
    ##
    # lib_name - uniq id, used lib name for instance
    def __init__(self, lib_name, id_client, abstractScheduler, Exit, path):
        super().__init__()

        self.id_client = id_client
        self.lib_name = lib_name
        
        self.abstractScheduler = abstractScheduler
        
        self.Exit = Exit
        self.loading = True
        self.path = path
        
        self.transaction_lock = Lock()
        
        self.in_pipe = deque()
        self.transaction = None
        
        self.transactions = []
        self.applied_transactions = set()
        self.incomming_transactions = []
             
    def location_of(self, filename):
        return os.path.join(self.path, filename)
        
    def isfile(self, filename):
        return os.path.isfile( self.location_of(filename) )
        
    def add(self, row):#thread-safe because deque is
        self.in_pipe.append(row)
        
    def apply(self, transactions, duration):
        origin = time()
        transactions = deque(transactions)
        
        while transactions and origin + duration > time(): 
            transaction = transactions.popleft()
            if transaction.id() in self.applied_transactions or not transaction.data:
                continue

            self.applied_transactions.add(transaction.id())

            for tmp in transaction.data:
                t,row = tmp[0], tmp[1:]
                if t == 'added':
                    fp, md5, size = row
                    self.abstractScheduler.add_file( fp, md5, size)
                elif t == 'removed':
                    _, md5, _ = row

                    self.abstractScheduler.remove_file(md5)
                elif t == 'struct':
                    replicat, struct = row
                    
                    self.abstractScheduler.update_structure(replicat, struct)

            for bucket in self.abstractScheduler.buckets():
                transaction.save(os.path.join(bucket.path, 'transactions'))
            
        transactions.clear()
            
    def check_incomming_transactions(self):
        transactions = set()
        buckets = self.abstractScheduler.buckets() #peut être access(0)??,
        replicat = self.abstractScheduler.replicat
        for bucket,_ in zip(buckets, range(replicat)):
            for tr in bucket.transactions():
                if tr.id() not in self.applied_transactions:
                    transactions.add(tr)
        
        self.incomming_transactions.extend( sorted(transactions) )
            
    def lock_all(self):
        delay = 2
        ttl = 120
        buckets = self.abstractScheduler.buckets()
        for bucket in buckets:
            if not bucket.try_lock(self.id_client, ttl): #can be async rewrite
                sleep(delay)
                return False
        
        sleep(delay)
        
        for bucket in buckets:
            if not bucket.is_locked(self.id_client):
                sleep(delay)
            return False
        
        return True
        
    def unlock_all(self):
        for bucket in self.abstractScheduler.buckets():
            bucket.unlock()
    
    def process(self):
        if not self.transaction:
            self.transaction = Transaction(self.id_client, self.lib_name)
        
        if( len(self.transaction) > size_transaction 
        or time() > self.transaction.time + delay_transaction):
            self.transactions.append(self.transaction)
            self.transaction = Transaction(self.id_client, self.lib_name)
        
        for k in range(min(len(self.in_pipe), size_transaction-len(self.transaction))):
            self.transaction.add(self.in_pipe.popleft())
            
        self.check_incomming_transactions()
        self.apply(self.incomming_transactions, 120/2)
        
        if self.transactions and self.lock_all():
            self.check_incomming_transactions()
            self.apply(self.incomming_transactions, 120/2)
            
            self.apply(self.transactions, 120/2)
            self.unlock_all()
   
    def store(self):
        if not self.applied_transactions:
            return 
        with open(self.location_of("applied_transactions.json"), "w") as f :
            json.dump(list(self.applied_transactions), f)   

    def load(self):
        if not self.isfile("applied_transactions.json"):
            return
            
        with open(self.location_of("applied_transactions.json"), "r") as f :
            self.applied_transactions = set(json.load(f))
   
    def reset_storage(self):
        if self.isfile('applied_transactions.json'):
            os.remove(self.location_of('applied_transactions.json'))
   
    def quick_restore(self):
        self.check_incomming_transactions()
        self.apply( self.incomming_transactions, 2**32 )
        
    def run(self):
        if self.loading:
            self.load()
        
        while not self.Exit.is_set():
            self.process()
            sleep(1)
            
        while self.in_pipe:
            self.process()
            sleep(1)
        
        self.store()
