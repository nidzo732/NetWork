"""
This file will define a program that will run on the main computer
For now you may see some random code i used to test the package
"""
from NetWork.networking import NWSocket, COMCODE_CHECKALIVE, COMCODE_ISALIVE
from NetWork.task import Task
from concurrent.futures import ProcessPoolExecutor
from threading import Thread
import atexit
import pickle
executor=ProcessPoolExecutor()
tasks={"-1":None}
class BadRequestError(Exception): pass

def executeTask(request, requestSocket):
    newTask=Task(marshaled=request)
    handler=executor.submit(newTask.target, *newTask.args, **newTask.kwargs)
    tasks[newTask.id]=handler
    requestSocket.send(COMCODE_TASK_STARTED)

def getResult(request, requestSocket):
    result=tasks[int(request)].result()
    requestSocket.send(pickle.dumps(result))
    
handlers={"TSK":executeTask, "RSL":getResult}
def requestHandler(requestSocket):
    request=requestSocket.recv()
    handlers[request[:3]](request[3:])

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
    