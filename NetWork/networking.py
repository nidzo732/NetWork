"""
This module implements various networking functions used throughout
the package

Created on Jan 13, 2013
"""
import socket

def getLocalIP():
    """
    Gets the local network IP address
    """
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("192.168.1.1", 80))
    return s.getsockname()[0]

def getDataFromSocket(sourcesocket):
    """
    Safely get the data from the socket
    """
    receivedData=b""
    while receivedData.find(b"MLEN")==-1:
        receivedData+=sourcesocket.recv(4096)
    sizelen=receivedData.find(b"MLEN")
    messageLenght=int(receivedData[0:sizelen])
    receivedData=receivedData[sizelen+4:]
    while len(receivedData)<messageLenght:
        receivedData+=sourcesocket.recv(messageLenght)
    sourcesocket.close()
    return receivedData
    
    
def parseRequest(commsocket, queue):    #Not yet complete
    queue.put(getDataFromSocket(commsocket))
    