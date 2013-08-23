"""
This module implements a socket classes used to safely handle
network messaging, message length and security.
"""
import socket

COMCODE_CHECKALIVE=b"ALV"
COMCODE_ISALIVE=b"IMALIVE"
ISALIVE_TIMEOUT=10
DEFAULT_TCP_PORT=32151
BUFFER_READ_LENGTH=4096
MESSAGE_LENGTH_DELIMITER=b"MLEN"
DEFAULT_LISTENING_ADDRESS="0.0.0.0"
LISTEN_QUEUE_LENGTH=5
DEFAULT_SOCKET_TIMEOUT=5.0

class InvalidMessageFormatError(OSError):pass
class MessageNotCompleteError(OSError):pass

    
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
            return False
            
        return response==COMCODE_ISALIVE
    
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
    
    def __del__(self):
        self.close()
    
NWSocket=NWSocketTCP    #set default socket used in the framework
