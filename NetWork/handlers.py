'''
Created on Feb 1, 2013

@author: nidzo
'''
from .networking import getDataFromSocket
    
def handleRequestMaster(rqSocket, commqueue):
    requestData=getDataFromSocket(rqSocket)
    commqueue.put(requestData)

