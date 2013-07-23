"""
This file will define a program that will run on the main computer
For now you may see some random code i used to test the package
"""
from NetWork.networking import NWSocket, COMCODE_CHECKALIVE, COMCODE_ISALIVE
from NetWork.task import Task
from NetWork.workerprocess import WorkerProcess
import NetWork.event as event
from threading import Thread
from multiprocessing import Manager, Event
import atexit
import pickle
class BadRequestError(Exception): pass

def executeTask(request, requestSocket):
    newTask=Task(marshaled=request)
    newProcess=WorkerProcess(request)
    tasks[newTask.id]=b=newProcess
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
    
handlers={b"TSK":executeTask, b"RSL":getResult, b"EXR":exceptionRaised,
          b"TRM":terminateTask, b"TRN":taskRunning, b"EXC":getException,
          b"EVS":setEvent, b"EVR":registerEvent,}

def requestHandler(requestSocket):
    request=requestSocket.recv()
    handlers[request[:3]](request[3:], requestSocket)
    requestSocket.close()

def onExit(listenerSocket):
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
            event.MasterAddress=masterAddress
            requestSocket.close()
            print("MASTER REGISTERED")
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
    while True:
        requestSocket=listenerSocket.accept()
        requestHandler(requestSocket)
    