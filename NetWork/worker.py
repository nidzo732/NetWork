"""
This file implements a worker class that is used to represent
one worker computer and send messages to that computer.
"""


class WorkerUnavailableError(Exception): pass


class DeadWorkerError(Exception):
    def __init__(self, id, message=None):
        self.id = id
        Exception.__init__(self, message)


import pickle

import NetWork.networking


class Worker:
#A class used to handle one worker
    def __init__(self, address, id):
        workerAvailable = NetWork.networking.NWSocket.checkAvailability(address)
        if not workerAvailable[0]:
            #Need a better message, I know 
            raise WorkerUnavailableError("Worker " + str(address) + " refused to cooperate")
        else:
            self.address = address
            self.realAddress = workerAvailable[1]
            self.id = id
            self.myTasks = {"-1": None}
            self.alive = True

    def sendRequest(self, type, contents):
        #Send message to ther worker
        if not self.alive:
            raise DeadWorkerError(self.id)
        try:
            workerSocket = NetWork.networking.NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(type + pickle.dumps(contents))
            workerSocket.recv()
            workerSocket.close()
        except OSError:
            self.alive = False
            raise DeadWorkerError(self.id)

    def sendRequestWithResponse(self, type, contents):
        #Send message to the worker and get the response
        if not self.alive:
            raise DeadWorkerError(self.id)
        try:
            workerSocket = NetWork.networking.NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(type + pickle.dumps(contents))
            response = workerSocket.recv()
            workerSocket.close()
            return pickle.loads(response)
        except OSError:
            self.alive = False
            raise DeadWorkerError(self.id)