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

running=False
tasks={-1:None}

def executeTask(request):
    newTask=Task(marshaled=request.getContents())
    newProcess=WorkerProcess(request.getContents())
    tasks[newTask.id]=newProcess
    tasks[newTask.id].start()
    request.respond(COMCODE_ISALIVE)

def getResult(request):
    id=int(request.getContents())
    result=tasks[id].getResult()
    request.respond(pickle.dumps(result))

def exceptionRaised(request):
    id=int(request.getContents())
    exceptionTest=tasks[id].exceptionRaised()
    request.respond(pickle.dumps(exceptionTest))

def terminateTask(request):
    id=int(request.getContents())
    tasks[id].terminate()

def taskRunning(request):
    id=int(request.getContents())
    status=tasks[id].running()
    request.respond(pickle.dumps(status))

def getException(request):
    id=int(request.getContents())
    exception=tasks[id].getException()
    request.respond(pickle.dumps(exception))

def setEvent(request):
    event.events[int(request.getContents())].set()

def registerEvent(request):
    id=int(request.getContents())
    event.events[id]=Event()

def checkAlive(request):
    if requestSocket.address==masterAddress:
        request.respond(COMCODE_ISALIVE)

def putOnQueue(request):
    idLength=request.getContents().find(b"ID")
    id=int(request.getContents()[:idLength])
    queue.queues[id].put(request.getContents()[idLength+2:])

def registerQueue(request):
    queue.queues[int(request.getContents())]=Queue()

def registerLock(request):
    lock.locks[int(request.getContents())]=Lock()
    lock.locks[int(request.getContents())].acquire()

def releaseLock(request):
    lock.locks[int(request.getContents())].release()
    
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
        handlers[request.type()](request)
        request.close()
        request=commqueue.get()
    for taskID in tasks:
        if taskID!=-1:
            tasks[taskID].terminate()
    

def requestReceiver(requestSocket, commqueue):
    receivedData=requestSocket.recv()
    commqueue.put(Command(receivedData, -1, requestSocket))

def onExit(listenerSocket, commqueue, handlerThread):
    if running:
        listenerSocket.close()
        commqueue.put(CMD_HALT)
        handlerThread.join()
    

if __name__=="__main__":
    listenerSocket=NWSocket()
    try:
        listenerSocket.listen()
    except OSError:
        print("Failed to start listening on the network")
        listenerSocket.close()
        exit()
    masterRegistered=False
    while not masterRegistered:
        try:
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
                masterRegistered=True
            else:
                raise BadRequestError
        except OSError as error:
            print ("There was a connection atempt but a network error happened", 
                   error)
        except BadRequestError:
            print("A request was received but it was not valid:", request)
        except KeyboardInterrupt:
            exit()
    workerManager=Manager().list(range(20))
    event.events={-1:None}
    event.runningOnMaster=False
    queue.queues={-1:None}
    queue.runningOnMaster=False
    lock.locks={-1:None}
    lock.runningOnMaster=False
    manager.runningOnMaster=False
    commqueue=Queue()
    handlerThread=Thread(target=requestHandler, args=(commqueue,))
    handlerThread.start()
    #Start receiving requests
    running=True
    atexit.register(onExit, listenerSocket, commqueue, handlerThread)
    try:
        while True:
            requestSocket=listenerSocket.accept()
            receiverThread=Thread(target=requestReceiver, 
                                  args=(requestSocket, commqueue))
            receiverThread.start()
    except KeyboardInterrupt:
        exit()
    