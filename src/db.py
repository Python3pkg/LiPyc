import sqlite3
import os
from datetime import datetime

from lipyc.Album import Album
from lipyc.File import File, FileMetadata

class DBFactory:
    def __init__(self, path):
        self.path = path
    
        if not os.path.isfile( os.path.join(path, 'metadata.db')) :
            self.conn = self.connect()
            self.create_tables()
        else:
            self.conn = self.connect()
        
        
    
    def __del__(self):
        self.conn.close()
       
    def close(self):
        self.conn.close()
        
    def connect(self):
        return sqlite3.connect(os.path.join(self.path, 'metadata.db'))
    
    def create_tables(self):
        print("creating tables")
        print()
        with self.conn:
            self.conn.execute('''CREATE TABLE albums 
            (id, name, datetime, subalbums, thumbails, files, inner_keys, PRIMARY KEY (`id`))''')
            
            self.conn.execute('CREATE TABLE first_layer_albums (id_album INT, PRIMARY KEY (`id_album`))')
            
            self.conn.execute('''CREATE TABLE inner_albums 
            (key, id_album, PRIMARY KEY (`key`))''')
            
            self.conn.execute('''CREATE TABLE files 
            (id, md5, filename, thumbnail, PRIMARY KEY (`id`))''')
            
            self.conn.execute('''CREATE TABLE file_metadata (id_file, datetime, year, month, 
            width, height, size, PRIMARY KEY (`id_file`))''')
        print("tables created")
    
    def save_albums(self, albums):
        data = [ album.sql() for album in albums]
        
        with self.conn:
            self.conn.executemany('''INSERT OR REPLACE INTO albums (id, name, 
            datetime, subalbums, thumbails, files, inner_keys) VALUES(?,?,?,?,?,?,?)''', data)
           
    def save_first_layer_albums(self, albums):
        data = [(album.id,) for album in albums]
        
        with self.conn:
            self.conn.executemany('''INSERT OR REPLACE INTO first_layer_albums 
            (id_album) VALUES (?)''', data)
            
    def save_file_metadata(self, metadatas):
        data = [ m.sql() for m in metadatas]
      
        with self.conn:
            self.conn.executemany('''INSERT OR REPLACE INTO file_metadata 
            (id_file, datetime, year, month, width, height, size) VALUES 
            (?,?,?,?,?,?,?) ''', data)
                
    def save_files(self, files):
        data = [ afile.sql() for afile in files]
        
        with self.conn:
            self.conn.executemany('''INSERT OR REPLACE INTO files (id, md5, 
            filename, thumbnail) VALUES (?,?,?,?)''', data)
        

        self.save_file_metadata( [afile.metadata for afile in files] )
    
    def save_inner_albums(self, inner_albums):
        data = [ ('|'.join(key), alb.id) for key, alb in inner_albums.items() ]
      
        with self.conn:
            self.conn.executemany('''INSERT OR REPLACE INTO inner_albums 
            (key, id_album) VALUES (?,?) ''', data)
    
    def build_file_metadata(self):
        metadata = {}
        
        with self.conn:
            for row in self.conn.execute('SELECT * FROM file_metadata'):
                tmp = FileMetadata()

                tmp.datetime = int(row[1])
                tmp.year = int(row[2])
                tmp.month = int(row[3])
                tmp.width = int(row[4])
                tmp.height = int(row[5])
                tmp.size = int(row[6])
                
                metadata[ int(row[0]) ] = tmp
                
        return metadata
    
    def build_files(self, scheduler):
        metadata = self.build_file_metadata()
        files={}
        
        with self.conn:
            for row in self.conn.execute('SELECT * FROM files'):
                tmp = File(int(row[0]), scheduler, row[1], row[2])
                tmp.thumbnail = row[3]
                
                metadata[int(row[0])].parent = tmp
                tmp.metadata = metadata[int(row[0])]
                
                files[int(row[0])] = tmp
        return files
    
    def build_albums(self, scheduler, files):
        albums0 = []
        albums = {}
        
        with self.conn:
            for row in self.conn.execute('SELECT * FROM albums'):
                tmp = Album(int(row[0]), scheduler, row[1], int(row[2]))
                tmp.thumbnail = row[4]
                
                if row[5]:
                    for id_file in row[5].split('|'):
                        tmp.add_file(files[int(id_file)]) 
                    
                tmp.inner_keys = row[6]
                if row[3]:
                    albums0.append( (row[3], tmp) )
                albums[ int(row[0]) ] = tmp

        for subalbums, album in albums0:
            if isinstance(subalbums, str):
                for id_album in subalbums.split('|'):
                    album.add_subalbum( albums[int(id_album)] )
            else:
                album.add_subalbum( albums[ id_album ] )
        return albums
    
    def build_first_layer_albums(self, albums):
        first_layer = set()
        
        with self.conn:
            for row in self.conn.execute('SELECT * FROM first_layer_albums'):
                first_layer.add( albums[int(row[0])] )
        
        return first_layer
        
    def build_inner_albums(self, albums):
        inner_albums = {}
        
        with self.conn:
            for row in self.conn.execute('SELECT * FROM inner_albums'):
                inner_albums[tuple(row[0].split('|'))] = albums[int(row[1])]
        
        return inner_albums
