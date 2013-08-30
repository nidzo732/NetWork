"""
This module implements a socket classes used to safely handle
network messaging, message length and security.
"""
import socket
import pickle
import hmac
import hashlib
from .request import Request

COMCODE_CHECKALIVE=b"ALV"
COMCODE_ISALIVE=b"IMALIVE"
ISALIVE_TIMEOUT=10
DEFAULT_TCP_PORT=32151
BUFFER_READ_LENGTH=4096
MESSAGE_LENGTH_DELIMITER=b"MLEN"
HASH_LENGTH_DELIMITER=b"HLEN"
DEFAULT_LISTENING_ADDRESS="0.0.0.0"
LISTEN_QUEUE_LENGTH=5
DEFAULT_SOCKET_TIMEOUT=5.0

class InvalidMessageFormatError(OSError):pass
class MessageNotCompleteError(OSError):pass
class UnauthenticatedMessage(OSError):pass
class KeyNotSet(OSError):pass

masterAddress=None

    
class NWSocketTCP:
    #Currently the default socket class that implements a
    #classic TCP communication
    def __init__(self, socketToUse=None, address=None):
        if socketToUse:
            self.internalSocket=socketToUse
        else:
            self.internalSocket=socket.socket(socket.AF_INET, 
                                              socket.SOCK_STREAM)
        
        self.internalSocket.setsockopt(socket.SOL_SOCKET, 
                                       socket.SO_REUSEADDR, 1)
        self.internalSocket.settimeout(DEFAULT_SOCKET_TIMEOUT)
        self.address=address
        
    def listen(self):
        #listen for incomming connections
        self.internalSocket.settimeout(None)
        self.internalSocket.bind((DEFAULT_LISTENING_ADDRESS, DEFAULT_TCP_PORT))
        self.internalSocket.listen(LISTEN_QUEUE_LENGTH)
    
    def recv(self):
        #safely receive all sent data
        receivedData=b""
        while receivedData.find(MESSAGE_LENGTH_DELIMITER)==-1:
            if not NWSocketTCP.checkMessageFormat(receivedData):
                raise InvalidMessageFormatError("Received string not formatted properly")
            newData=self.internalSocket.recv(BUFFER_READ_LENGTH)
            if len(newData)==0:
                raise MessageNotCompleteError("Socket got closed before receiving the entire message")
            receivedData+=newData
        if not NWSocket.checkMessageFormat(receivedData):
            raise InvalidMessageFormatError("Received string not formatted properly")
        sizelen=receivedData.find(MESSAGE_LENGTH_DELIMITER)
        messageLength=int(receivedData[0:sizelen])
        receivedData=receivedData[sizelen+len(MESSAGE_LENGTH_DELIMITER):]
        while len(receivedData)<messageLength:
            newData=self.internalSocket.recv(BUFFER_READ_LENGTH)
            if len(newData)==0:
                raise MessageNotCompleteError("Socket got closed before receiving the entire message")
            receivedData+=newData
        return receivedData
    
    def send(self, data):
        #send given data
        dataLength=str(len(data)).encode(encoding="ASCII")
        message=dataLength+MESSAGE_LENGTH_DELIMITER+data
        self.internalSocket.sendall(message)
    
    def connect(self, address):
        #connect to the address
        self.address=address
        self.internalSocket.connect((address, DEFAULT_TCP_PORT))
    
    def accept(self):
        #accept a connection request and return a communication socket
        requestData=self.internalSocket.accept()
        return NWSocket(requestData[0], requestData[1][0])
    
    
    def close(self):
        #close the socket
        self.internalSocket.close()
    
    @staticmethod
    def checkAvailability(address):
        #check if there's a worker on the address     
        testSocket=NWSocket()
        try:  
            testSocket.connect(address) 
            testSocket.send(COMCODE_CHECKALIVE)
            response=testSocket.recv()
        except OSError:
            return (False, None)
            
        return (response==COMCODE_ISALIVE, testSocket.address)
    
    @staticmethod
    def checkMessageFormat(message):
        #check if a message fits the format
        if not message:
            return True
        elif not (message[0] in range(48, 59)):
            return False
        else:
            for i in enumerate(message):
                if not i[1] in range(48, 59):
                    p=i[0]
                    break
            else:
                return True
            message=message[p:]
            if len(message)==len(MESSAGE_LENGTH_DELIMITER):
                return message==MESSAGE_LENGTH_DELIMITER
            elif len(message)<len(MESSAGE_LENGTH_DELIMITER):
                return message==MESSAGE_LENGTH_DELIMITER[:len(message)]
            else:
                return message[:len(MESSAGE_LENGTH_DELIMITER)]==MESSAGE_LENGTH_DELIMITER
                    
        return True
    
class NWSocketHMAC(NWSocketTCP):
    listenerKey=None
    
    def __init__(self, socketToUse=None, parameters=None):
        if socketToUse:
            NWSocketTCP.__init__(self, socketToUse, parameters[0])
            self.key=parameters[1]
        else:
            NWSocketTCP.__init__(self)
    
    def listen(self):
        if not self.listenerKey:
            raise KeyNotSet("The HMAC key for listener sockets was not set")
        NWSocketTCP.listen(self)

    def connect(self, parameters):
        NWSocketTCP.connect(self, parameters[0])
        self.address=parameters[0]
        self.key=parameters[1]
    
    def recv(self):
        receivedData=NWSocketTCP.recv(self)
        try:
            hashLength=int(receivedData[:receivedData.find(HASH_LENGTH_DELIMITER)])
            receivedData=receivedData[receivedData.find(HASH_LENGTH_DELIMITER)+len(HASH_LENGTH_DELIMITER):]
        except ValueError:
            raise InvalidMessageFormatError("Received string not formatted properly")
        
        message=receivedData[:-hashLength]
        receivedHash=receivedData[-hashLength:]
        messageHash=hmac.new(key=self.key, msg=message, digestmod=hashlib.sha256)
        if hmac.compare_digest(messageHash.digest(), receivedHash):
            return message
        else:
            raise UnauthenticatedMessage("Received message came from an unathhenticated source")
    
    def send(self, data):
        messageHash=hmac.new(key=self.key, msg=data, digestmod=hashlib.sha256)
        hash=messageHash.digest()
        message=str(len(hash)).encode(encoding="ASCII")+HASH_LENGTH_DELIMITER
        message+=data+hash
        NWSocketTCP.send(self, message)
    
    def accept(self):
        requestData=self.internalSocket.accept()
        return NWSocketHMAC(requestData[0], (requestData[1][0], self.listenerKey))
    
    @staticmethod
    def setListenerKey(key):
        NWSocketHMAC.listenerKey=key
        
NWSocket=NWSocketTCP    #set default socket used in the framework

def sendRequest(type, contents):
    request=Request(type, contents)
    masterSocket=NWSocket()
    masterSocket.connect(masterAddress)
    masterSocket.send(request.getType()+pickle.dumps(request.getContents()))
    masterSocket.close()

def sendRequestWithResponse(type, contents):
    request=Request(type, contents)
    masterSocket=NWSocket()
    masterSocket.connect(masterAddress)
    masterSocket.send(request.getType()+pickle.dumps(request.getContents()))
    receivedData=masterSocket.recv()
    masterSocket.close()
    return receivedData
    
    
