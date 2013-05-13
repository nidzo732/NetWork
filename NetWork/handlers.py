'''
Created on Feb 1, 2013

@author: nidzo
'''
    
def handleRequestMaster(rqSocket, commqueue):
    requestData=rqSocket.recv()
    commqueue.put(requestData)

