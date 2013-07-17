'''
Created on Feb 1, 2013

@author: nidzo
'''
CNT_WORKERS=0

def receiveSocketData(socket, commqueue):
    commqueue.put(socket.recv())
    socket.close()

def setEvent(request, controlls, commqueue):
    for worker in controlls[CNT_WORKERS]:
        if worker.alive:
            worker.setEvent(int(request))
        
handlerList["EVS"]=setEvent
