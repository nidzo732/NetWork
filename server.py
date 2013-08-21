"""
This program runs on worker computers and waits for requests from the master.
It is responsible for running tasks and passing them data sent from the master.

When it starts, it waits for the first message from the master, which should
be COMMCODE_CHECKALIVE and it responds with COMCODE_ISALIVE.
Once the master is registered the mainloop starts receiving messages
from the master. The messages start with a 3 letter code that determines
their type, the mainloop reads that code and runs a handler function associated
with that code. Message codes can be seen in NetWork.commcodes.
"""
from NetWork.networking import NWSocket, COMCODE_CHECKALIVE, COMCODE_ISALIVE
from NetWork.task import Task
from NetWork.workerprocess import WorkerProcess
import NetWork.queue as queue
import NetWork.event as event
import NetWork.lock as lock
import NetWork.manager as manager
from threading import Thread
from multiprocessing import Manager, Event, Queue, Lock
from NetWork.commcodes import *
import atexit
import pickle
from NetWork.command import Command
class BadRequestError(Exception): pass

def executeTask(request, requestSocket):
    newTask=Task(marshaled=request)
    newProcess=WorkerProcess(request)
    tasks[newTask.id]=newProcess
    tasks[newTask.id].start()
    requestSocket.send(COMCODE_ISALIVE)

def getResult(request, requestSocket):
    id=int(request)
    result=tasks[id].getResult()
    requestSocket.send(pickle.dumps(result))

def exceptionRaised(request, requestSocket):
    id=int(request)
    exceptionTest=tasks[id].exceptionRaised()
    requestSocket.send(pickle.dumps(exceptionTest))

def terminateTask(request, requestSocket):
    id=int(request)
    tasks[id].terminate()

def taskRunning(request, requestSocket):
    id=int(request)
    status=tasks[id].running()
    requestSocket.send(pickle.dumps(status))

def getException(request, requestSocket):
    id=int(request)
    exception=tasks[id].getException()
    requestSocket.send(pickle.dumps(exception))

def setEvent(request, requestSocket):
    event.events[int(request)].set()

def registerEvent(request, requestSocket):
    id=int(request)
    event.events[id]=Event()

def checkAlive(request, requestSocket):
    if requestSocket.address==masterAddress:
        requestSocket.send(COMCODE_ISALIVE)

def putOnQueue(request, requestSocket):
    idLength=request.find(b"ID")
    id=int(request[:idLength])
    queue.queues[id].put(request[idLength+2:])

def registerQueue(request, requestSocket):
    queue.queues[int(request)]=Queue()

def registerLock(request, requestSocket):
    lock.locks[int(request)]=Lock()
    lock.locks[int(request)].acquire()

def releaseLock(request, requestSocket):
    lock.locks[int(request)].release()
    
handlers={b"TSK":executeTask, b"RSL":getResult, b"EXR":exceptionRaised,
          b"TRM":terminateTask, b"TRN":taskRunning, b"EXC":getException,
          b"EVS":setEvent, b"EVR":registerEvent, b"ALV":checkAlive, 
          b"QUP":putOnQueue, b"QUR":registerQueue,
          CMD_REGISTER_LOCK:registerLock, CMD_RELEASE_LOCK:releaseLock}

def requestHandler(commqueue):
    #Give requests to handler functions
    request=commqueue.get()
    while request!=CMD_HALT:
        #print(request)
        handlers[request.type()](request.getContents(), request.socket)
        request.close()
        request=commqueue.get()
    for task in tasks:
        task.terminate()
    

def requestReceiver(requestSocket, commqueue):
    receivedData=requestSocket.recv()
    commqueue.put(Command(receivedData, -1, requestSocket))

def onExit(listenerSocket, commqueue, handlerThread):
    listenerSocket.close()
    commqueue.put(CMD_HALT)
    handlerThread.join()
    

if __name__=="__main__":
    listenerSocket=NWSocket()
    commqueue=Queue()
    atexit.register(onExit, listenerSocket, commqueue, handlerThread)
    try:
        listenerSocket.listen()
        requestSocket=listenerSocket.accept()
        request=requestSocket.recv()
        if request==COMCODE_CHECKALIVE:
            #Register the master
            requestSocket.send(COMCODE_ISALIVE)
            masterAddress=requestSocket.address
            event.masterAddress=masterAddress
            queue.masterAddress=masterAddress
            lock.masterAddress=masterAddress
            manager.masterAddress=masterAddress
            requestSocket.close()
            print("MASTER REGISTERED with address", masterAddress)
        else:
            raise BadRequestError
    except OSError:
        print ("Network communication failed")
        exit()
    except BadRequestError:
        print("Master did not send a proper request")
        exit()
    tasks={-1:None}
    workerManager=Manager().list(range(20))
    event.events={-1:None}
    event.runningOnMaster=False
    queue.queues={-1:None}
    queue.runningOnMaster=False
    lock.locks={-1:None}
    lock.runningOnMaster=False
    manager.runningOnMaster=False
    handlerThread=Thread(target=requestHandler, args=(commqueue,))
    handlerThread.start()
    #Start receiving requests
    while True:
        requestSocket=listenerSocket.accept()
        receiverThread=Thread(target=requestReceiver, args=(requestSocket, commqueue))
        receiverThread.start()
    