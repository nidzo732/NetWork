"""
This file implements a WorkGroup class. It will define a group of worker
computers, distribute their work and provide communication between them.

Created on Jan 11, 2013
"""

from multiprocessing import Process, Queue, Manager, Event
from .networking import NWSocket
from .handlers import handleRequestMaster
from threading import Thread
from .worker import Worker, WorkerUnavailableError

#Positions in the WorkGroup.controlls list that is used for communication 
#between the processes
CNT_WORKERS=0
CNT_SHOULD_STOP=2
CNT_LISTEN_SOCKET=3
CNT_WORKER_COUNT=4

CMD_HALT=b"HLT"     #Put this on the queue to stop the _mainloopcontroll

#Exceptions used by workgroup
class NoWorkersError(Exception):pass


class WorkGroup:    #Not yet implemented
    """
    This class is used by the "master" computer. A WorkGroup object will
    distribute tasks to the worker computers and manage communication between 
    them (Locks, Queues, Events ...)
    """

    def __init__(self, workerAddresses, skipBadWorkers=True):
        """
        Create a WorkGroup object
        
        workerAddresses-> a list of IPs (or other connection parameters that
            should be used to communicate with the workers
        skipBadWorkers-> should I skip bad workers and continue or raise an
        exception
        
        If no workers are available NoWorkersError will be raised
        """
        #The manager will be used for communication between the mainloops
        self.controlls=Manager().list(range(10)) 
        self.controlls[CNT_WORKERS]=[]
        self.controlls[CNT_WORKER_COUNT]=0
        self.listenerSocket=NWSocket()
        #Temporary worker list, future value of controlls[CNT_WORKERS]
        workerList=[]
        for workerAddress in workerAddresses:
            try:
                newWorker=Worker(workerAddress,
                                 self.controlls[CNT_WORKER_COUNT+1])
                workerList.append(newWorker)
                self.controlls[CNT_WORKER_COUNT]+=1
            except WorkerUnavailableError as workerError:
                if not skipBadWorkers:
                    raise workerError
        if not workerList:
            raise NoWorkersError("No workers were successfuly added")
        else:
            self.controlls[CNT_WORKERS]=workerList
    
    def mainloop(self):
        """
        Run the event loop, this should be started before doing any real work
        """
        self._mainloopcontroll=Process(target=WorkGroup._mainloopControll, 
                                      args=(self.queue, self.controlls))
        self._mainloopreceiver=Process(target=WorkGroup._mainloopReceiver, 
                                       args=(self.queue, self.controlls, 
                                             self.listenerSocket))
        self._mainloopcontroll.daemon=True
        self._mainloopreceiver.daemon=True
        self._mainloopcontroll.start()
        self._mainloopreceiver.start()
    
    def halt(self):
        """
        Halt the mainloops
        """
        self.queue.put(CMD_HALT)
        self.listenerSocket.close()
        self._mainloopcontroll.join()
        self._mainloopreceiver.terminate()
    
    def __del__(self):
        if self._mainloopcontroll.is_alive() or self._mainloopreceiver.is_alive():
            self.halt()
    
    #An event loop that receives the network input from the worker computers
    #and sends it to the comm Queue
    @staticmethod
    def _mainloopReceiver(commqueue, controlls, listenerSocket):     
        #Not yet implemented
        
        listenerSocket.bind()
        listenerSocket.listen()
        while True:
            receivedRequestData=listenerSocket.accept()
            handlerThread=Thread(target=handleRequestMaster, 
                                 args=(receivedRequestData, commqueue))
            handlerThread.start()
        

    #An event loop that receives tasks through the commqueue Queue and acts
    #accordingly, not yet implemented
    @staticmethod
    def _mainloopControll(commqueue, controlls):    
        job=commqueue.get()
        while job!=CMD_HALT:
            pass
