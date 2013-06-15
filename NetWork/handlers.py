'''
Created on Feb 1, 2013

@author: nidzo
'''

CMD_SOCKET_MESSAGE=b"SCK"  

def receiveSocketData(socket, commqueue):
    commqueue.put(CMD_SOCKET_MESSAGE+socket.recv())

