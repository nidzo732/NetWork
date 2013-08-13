"""
This is the server program that runs on the worker nodes and executes the
requests from the master computer.
The main loop runs a server socket and recevies messages from the master,
each message begins with a 3-character code (codes are defined in
NetWork.commcodes) that determines the type of the message. The message
is passed to the requestHandler that looks for the 3-character code in the
handlers dictionary, each code is associated with a handler function that
parses the request and acts accordingly, the communication socket is also 
passed to the handler in case it needs to respond to the request. 
Currently there are no special parameters for this program, just leave it
running on the worker nodes.
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
class BadRequestError(Exception): pass

def executeTask(request, requestSocket):
    #Get new task from the master and run it in a separate process
    newTask=Task(marshaled=request)
    newProcess=WorkerProcess(request)
    tasks[newTask.id]=b=newProcess
    tasks[newTask.id].start()
    requestSocket.send(COMCODE_ISALIVE)

def getResult(request, requestSocket):
    #Get the value returned by a submited task
    id=int(request)
    result=tasks[id].getResult()
    requestSocket.send(pickle.dumps(result))

def exceptionRaised(request, requestSocket):
    #Check if a task has raied an exception
    id=int(request)
    exceptionTest=tasks[id].exceptionRaised()
    requestSocket.send(pickle.dumps(exceptionTest))

def terminateTask(request, requestSocket):
    #Terminate a running task
    id=int(request)
    tasks[id].terminate()

def taskRunning(request, requestSocket):
    #Check if the task is still running
    id=int(request)
    status=tasks[id].running()
    requestSocket.send(pickle.dumps(status))

def getException(request, requestSocket):
    #Returns the exception that the task has raised
    id=int(request)
    exception=tasks[id].getException()
    requestSocket.send(pickle.dumps(exception))

def setEvent(request, requestSocket):
    #Sets an event, anything on this computer that was waiting for that event
    #will be waken up
    event.events[int(request)].set()

def registerEvent(request, requestSocket):
    #Add a new event to the event list
    id=int(request)
    event.events[id]=Event()

def checkAlive(request, requestSocket):
    #Used when the master starts again and check again if the worker is alive
    if requestSocket.address==masterAddress:
        requestSocket.send(COMCODE_ISALIVE)

def putOnQueue(request, requestSocket):
    #Puts the received data on a queue
    idLength=request.find(b"ID")
    id=int(request[:idLength])
    queue.queues[id].put(request[idLength+2:])

def registerQueue(request, requestSocket):
    #Add a new queue to the queue list
    queue.queues[int(request)]=Queue()

def registerLock(request, requestSocket):
    #Add a new lock to the lock list
    lock.locks[int(request)]=Lock()
    lock.locks[int(request)].acquire()

def releaseLock(request, requestSocket):
    #Release a lock on this computer, first task that tried to acquire
    #that lock will be waken up
    lock.locks[int(request)].release()
    
#Theese determine the functions that will be used to handle messages
#beginning with 3-character identifiers
handlers={b"TSK":executeTask, b"RSL":getResult, b"EXR":exceptionRaised,
          b"TRM":terminateTask, b"TRN":taskRunning, b"EXC":getException,
          b"EVS":setEvent, b"EVR":registerEvent, b"ALV":checkAlive, 
          b"QUP":putOnQueue, b"QUR":registerQueue,
          CMD_REGISTER_LOCK:registerLock, CMD_RELEASE_LOCK:releaseLock}

def requestHandler(requestSocket):
    #Receives the request from the socket and passes it to the apropriate
    #handler function
    request=requestSocket.recv()
    handlers[request[:3]](request[3:], requestSocket)
    requestSocket.close()

def onExit(listenerSocket):
    #Cleanup function to terminate the task and close the sockets when
    #the program is closed, NOT YET COMPLETED
    listenerSocket.close()  

if __name__=="__main__":
    listenerSocket=NWSocket()
    atexit.register(onExit, listenerSocket)
    try:
        listenerSocket.listen()
        requestSocket=listenerSocket.accept()
        request=requestSocket.recv()
        if request==COMCODE_CHECKALIVE:
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
    #Start receiving requests
    while True:
        requestSocket=listenerSocket.accept()
        requestHandler(requestSocket)
    