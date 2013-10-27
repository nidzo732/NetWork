"""
This program runs on worker computers and waits for requests from the master.
It is responsible for running tasks and passing them data sent from the master.

When it starts, it waits for the first message from the master, which should
be COMMCODE_CHECKALIVE and it responds with COMCODE_ISALIVE.
Once the master is registered the mainloop starts receiving messages
from the master. The messages start with a 3 letter code that determines
their type, the mainloop reads that code and runs a handler function associated
with that code. Core message codes can be seen in NetWork.commcodes.
"""
from threading import Thread
import atexit
import pickle

from NetWork.networking import COMCODE_CHECKALIVE, COMCODE_ISALIVE
from NetWork.workerprocess import WorkerProcess
import NetWork.queue as queue
import NetWork.event as event
import NetWork.lock as lock
import NetWork.manager as manager
import NetWork.semaphore as semaphore
from NetWork.commcodes import *
from NetWork.request import Request
from NetWork import networking
from NetWork.args import getArgs


class BadRequestError(Exception): pass


plugins = [event, queue, lock, manager, semaphore]

running = False
tasks = {-1: None}


def executeTask(request):
    newTask = request["TASK"]
    newProcess = WorkerProcess(newTask)
    tasks[newTask.id] = newProcess
    tasks[newTask.id].start()


def getResult(request):
    id = request["ID"]
    result = tasks[id].getResult()
    request.respond(result)


def exceptionRaised(request):
    id = request["ID"]
    exceptionTest = tasks[id].exceptionRaised()
    request.respond(exceptionTest)


def terminateTask(request):
    id = request["ID"]
    tasks[id].terminate()


def taskRunning(request):
    id = request["ID"]
    status = tasks[id].running()
    request.respond(status)


def getException(request):
    id = request["ID"]
    exception = tasks[id].getException()
    request.respond(exception)


def checkAlive(request):
    if requestSocket.address == masterAddress:
        request.respond(COMCODE_ISALIVE)

handlers = {CMD_SUBMIT_TASK: executeTask, CMD_GET_RESULT: getResult,
            CMD_CHECK_EXCEPTION: exceptionRaised,
            CMD_TERMINATE_TASK: terminateTask,
            CMD_TASK_RUNNING: taskRunning, CMD_GET_EXCEPTION: getException,
            b"ALV": checkAlive}


def requestHandler(request):
    handlers[request.getType()](request)
    request.close()


def requestReceiver(requestSocket):
    try:
        receivedData = requestSocket.recv()
    except OSError as error:
        print("Communication failed from", requestSocket.address, error)
        return
    if receivedData == b"ALV" and requestSocket.address == masterAddress:
        requestSocket.send(COMCODE_ISALIVE)
    elif not receivedData[:3] in handlers:
        print("Request came with an invalid identifier code", receivedData[:3])
    else:
        requestHandler(Request(receivedData[:3], pickle.loads(receivedData[3:]), -1, requestSocket))


def onExit(listenerSocket):
    if running:
        listenerSocket.close()


if __name__ == "__main__":
    args = getArgs()
    networking.setUp(args.socket_type, args.netArgs)
    listenerSocket = networking.NWSocket()
    try:
        listenerSocket.listen()
    except OSError as error:
        print("Failed to start listening on the network", error)
        listenerSocket.close()
        exit()
    masterRegistered = False
    while not masterRegistered:
        try:
            requestSocket = listenerSocket.accept()
            request = requestSocket.recv()
            if request == COMCODE_CHECKALIVE:
                #Register the master
                requestSocket.send(COMCODE_ISALIVE)
                masterAddress = requestSocket.address
                if args.socket_type == "AES+HMAC":
                    networking.masterAddress = (masterAddress, args.master_hmac_key,
                                                args.master_aes_key)
                elif args.socket_type == "HMAC":
                    networking.masterAddress = (masterAddress, args.master_hmac_key)
                elif args.socket_type == "AES":
                    networking.masterAddress = (masterAddress, args.master_aes_key)
                else:
                    networking.masterAddress = masterAddress
                requestSocket.close()
                print("MASTER REGISTERED with address", masterAddress)
                masterRegistered = True
            else:
                raise BadRequestError
        except OSError as error:
            print("There was a connection atempt but a network error happened",
                  error)
        except BadRequestError:
            print("A request was received but it was not valid:", request)
        except KeyboardInterrupt:
            exit()
    for plugin in plugins:
        plugin.workerInit()
        handlers.update(plugin.workerHandlers)
    #Start receiving requests
    running = True
    atexit.register(onExit, listenerSocket)
    try:
        while True:
            try:
                requestSocket = listenerSocket.accept()
            except OSError as error:
                print("There was a connection attempt but a network error occured", error)
                continue
            handlerThread = Thread(target=requestReceiver, args=(requestSocket,))
            handlerThread.start()
    except KeyboardInterrupt:
        exit()
