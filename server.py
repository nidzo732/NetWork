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
from NetWork.networking import COMCODE_CHECKALIVE, COMCODE_ISALIVE
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
from NetWork.request import Request
from NetWork import networking
from NetWork.args import getArgs
class BadRequestError(Exception): pass

running=False
tasks={-1:None}

def executeTask(request):
    newTask=request["TASK"]
    newProcess=WorkerProcess(newTask)
    tasks[newTask.id]=newProcess
    tasks[newTask.id].start()
    request.respond(COMCODE_ISALIVE)

def getResult(request):
    id=request["ID"]
    result=tasks[id].getResult()
    request.respond(pickle.dumps(result))

def exceptionRaised(request):
    id=request["ID"]
    exceptionTest=tasks[id].exceptionRaised()
    request.respond(pickle.dumps(exceptionTest))

def terminateTask(request):
    id=request["ID"]
    tasks[id].terminate()

def taskRunning(request):
    id=request["ID"]
    status=tasks[id].running()
    request.respond(pickle.dumps(status))

def getException(request):
    id=request["ID"]
    exception=tasks[id].getException()
    request.respond(pickle.dumps(exception))

def setEvent(request):
    event.events[request["ID"]].set()

def registerEvent(request):
    id=request["ID"]
    event.events[id]=Event()

def checkAlive(request):
    if requestSocket.address==masterAddress:
        request.respond(COMCODE_ISALIVE)

def putOnQueue(request):
    id=request["ID"]
    queue.queues[id].put(request["DATA"])

def registerQueue(request):
    queue.queues[request["ID"]]=Queue()

def registerLock(request):
    lock.locks[request["ID"]]=Lock()
    lock.locks[request["ID"]].acquire()

def releaseLock(request):
    lock.locks[request["ID"]].release()
    
handlers={b"TSK":executeTask, b"RSL":getResult, b"EXR":exceptionRaised,
          b"TRM":terminateTask, b"TRN":taskRunning, b"EXC":getException,
          b"EVS":setEvent, b"EVR":registerEvent, b"ALV":checkAlive, 
          b"QUP":putOnQueue, b"QUR":registerQueue,
          CMD_REGISTER_LOCK:registerLock, CMD_RELEASE_LOCK:releaseLock}

def requestHandler(request):
    handlers[request.getType()](request)
    request.close()
    

def requestReceiver(requestSocket):
    try:
        receivedData=requestSocket.recv()
    except OSError:
        print("Communication failed from", requestSocket.address)
    if receivedData==b"ALV" and requestSocket.address==masterAddress:
        requestSocket.send(COMCODE_ISALIVE)
    elif not receivedData[:3] in handlers:
        print("Request came with an invalid identifier code", receivedData[:3])
    else: 
        requestHandler(Request(receivedData[:3], pickle.loads(receivedData[3:]), -1, requestSocket))

def onExit(listenerSocket):
    if running:
        listenerSocket.close()

    
    

if __name__=="__main__":
    args=getArgs()
    networking.setUp(args.socket_type, args.netArgs)
    listenerSocket=networking.NWSocket()
    try:
        listenerSocket.listen()
    except OSError as error:
        print("Failed to start listening on the network", error)
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
                if args.socket_type=="AES+HMAC":
                    networking.masterAddress=(masterAddress, args.master_hmac_key,
                                              args.master_aes_key)
                elif args.socket_type=="HMAC":
                    networking.masterAddress=(masterAddress, args.master_hmac_key)
                elif args.socket_type=="AES":
                    networking.masterAddress=(masterAddress, args.master_aes_key)
                else:
                    networking.masterAddress=masterAddress
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
    #Start receiving requests
    running=True
    atexit.register(onExit, listenerSocket)
    try:
        while True:
            requestSocket=listenerSocket.accept()
            handlerThread=Thread(target=requestReceiver, args=(requestSocket,))
            handlerThread.start()
    except KeyboardInterrupt:
        exit()
    