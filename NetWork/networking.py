"""
This module implements various networking functions used throughout
the package

Created on Jan 13, 2013
"""
import socket

COMCODE_CHECKALIVE=b"ALV"
COMCODE_ISALIVE=b"IMALIVE"
ISALIVE_TIMEOUT=10
DEFAULT_LISTENING_PORT=32151
BUFFER_READ_LENGTH=4096
MESSAGE_LENGTH_DELIMITER=b"MLEN"
class acceptedRequest:
    def __init__(self, commSocket, address):
        self.address=address
        self.commSocket=commSocket


class nwSocket:

    def __init__(self, socketToUse=None):
        if socketToUse:
            self.internalSocket=socketToUse
        else:
            self.internalSocket=socket.socket(socket.AF_INET, 
                                              socket.SOCK_STREAM)
        
        self.internalSocket.setsockopt(socket.SOL_SOCKET, 
                                       socket.SO_REUSEADDR, 1)
    def bind(self):
        self.internalSocket.bind(("0.0.0.0", DEFAULT_LISTENING_PORT))

    def listen(self):
        self.internalSocket.listen(5)
    
    def recv(self):
        receivedData=b""
        while receivedData.find(MESSAGE_LENGTH_DELIMITER)==-1:
            receivedData+=self.internalSocket.recv(4096)
        sizelen=receivedData.find(MESSAGE_LENGTH_DELIMITER)
        messageLenght=int(receivedData[0:sizelen])
        receivedData=receivedData[sizelen+4:]
        while len(receivedData)<messageLenght:
            receivedData+=self.internalSocket.recv(messageLenght)
        self.internalSocket.close()
        return receivedData

    def send(self, data: bytes)-> bytes:
        dataLength=bytes(str(len(data)), encoding="utf-8")
        message=dataLength+MESSAGE_LENGTH_DELIMITER+data
        self.internalSocket.sendall(message)
    
    def connect(self, *connectparams):
        self.internalSocket.connect(*connectparams)
    
    def accept(self):
        requestData=self.internalSocket.accept()
        return acceptedRequest(nwSocket(requestData[0]), requestData[1])
    
    
    def close(self):
        self.internalSocket.close()
    
    def __del__(self):
        self.close()


    
