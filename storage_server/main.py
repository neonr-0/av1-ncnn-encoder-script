import os
import subprocess
import glob
import socket
import tqdm
import pickle
from threading import Thread
from socketserver import ThreadingMixIn
import hashlib


#settings
store_folder = './tmp/' # path to store all data 
#network
host = "0.0.0.0"
server_port = 7890 # change if need
BUFFER_SIZE = 4096 # send 4096 bytes each time step

def GetHashInfo(Path):
    with open(Path,"rb") as f:
        bytes = f.read() # read entire file as bytes
        readable_hash = hashlib.sha256(bytes).hexdigest()
        return readable_hash

class ClientThread(Thread):
    def __init__(self,ip,port,sock):
        Thread.__init__(self)
        self.ip = ip
        self.port = port
        self.sock = sock

    def run(self):    
        self.sock.settimeout(10)
        #get file data
        dataFileInfo = self.sock.recv(BUFFER_SIZE)
        dataFileInfo = pickle.loads(dataFileInfo)
        progress = tqdm.tqdm(range(dataFileInfo.get('filesize')), f"Receiving {dataFileInfo.get('filename')}", unit="B", unit_scale=True, unit_divisor=1024)
        SaveFileName = store_folder+dataFileInfo.get('filename')
        FileHash = dataFileInfo.get('hash')
        if dataFileInfo.get('isImgFile'):
            if not os.path.isdir(store_folder+os.path.dirname(dataFileInfo.get('filename'))):
                os.makedirs(store_folder+os.path.dirname(dataFileInfo.get('filename')))
            SaveFileName = store_folder+dataFileInfo.get('filename')         
        self.sock.send(b'ok') #send confirmation message
        f = open(SaveFileName,'wb')
        while True:
            try:
                bytes_read = self.sock.recv(BUFFER_SIZE)     
            except socket.timeout as err:
                f.close() 
                self.sock.close()
                break       
            except socket.error as err:
                f.close() 
                self.sock.close()
                break   
            if not bytes_read:
                f.close() 
                self.sock.close()
                break   
            if len(bytes_read)>=18:
                pythonEOF = bytes_read[-18:]
                if bytes_read[-18:] == b'PYTHON_SPECIAL_EOF': #message ending
                    bytes_read = bytes_read[:-18]
                    f.write(bytes_read)
                    f.close()
                    break
            f.write(bytes_read)
            # update the progress bar
            progress.update(len(bytes_read))
        try:
            f.close()
        except:
            print('error closing file')
        SavedFileHash = GetHashInfo(SaveFileName)
        if FileHash != SavedFileHash:
            try:
                self.sock.send(b'error')
            except:
                return
        else:
            self.sock.send(b'ok')
        self.sock.close()        



if __name__== '__main__':
    tcpsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcpsock.bind((host, server_port))
    print(f'Server started at port:{server_port}')
    while True:
        tcpsock.listen(5)
        (conn, (ip,port)) = tcpsock.accept()
        newthread = ClientThread(ip,port,conn)
        newthread.start()
