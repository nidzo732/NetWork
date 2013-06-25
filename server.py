"""
This file will define a program that will run on the main computer
For now you may see some random code i used to test the package
"""
from NetWork.networking import NWSocket, COMCODE_CHECKALIVE, COMCODE_ISALIVE
from NetWork.task import Task
from NetWork.workerprocess import WorkerProcess
from threading import Thread
import atexit
import pickle
class BadRequestError(Exception): pass
tasks={-1:None}

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
    
handlers={b"TSK":executeTask, b"RSL":getResult, b"EXR":exceptionRaised}
def requestHandler(requestSocket):
    request=requestSocket.recv()
    handlers[request[:3]](request[3:], requestSocket)

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
    while True:
        requestSocket=listenerSocket.accept()
        handlerThread=Thread(target=requestHandler, args=(requestSocket,))
        handlerThread.start()
    