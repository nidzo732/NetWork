"""
This file implements a WorkGroup class. It will define a group of worker
computers, distribute their work and provide communication between them.

Created on Jan 11, 2013
"""

from .parsers import parseIPRange
from .worker import Worker
from multiprocessing import Process, Queue, Manager

#Positions in the WorkGroup.controlls list that is used for communication between
#the processes
_CNT_WORKERS=0

#Exceptions used by workgroup
class NoWorkersError(Exception):pass

#An event loop that will receive the network input from the worker computers
#and sends it to the comm Queue
def _mainloopReceiver(comm, controlls):     #Not yet implemented
    pass

#An event loop that will receive tasks through the comm Queue and act
#accordingly
def _mainloopControll(comm, controlls):     #Not yet implemented
    job=comm.get()
    while job!="HALT":
        print("GOT A JOB", job)
        job=comm.get()

class WorkGroup:    #Not yet implemented
    """
    This class is used by the "master" computer. A WorkGroup object will
    distribute tasks to the worker computers and manage communication between 
    them (Locks, Queues, Events ...)
    """

    def __init__(self, iprange=None, workers=None, port=32151):
        """
        Create a WorkGroup object
        
        iprange-> a tuple that contains the first and last address 
                of the computers in the group, __init__ will try to 
                communicate with each address in the range and check 
                is it available for work
        workers-> an iterable that contains workers that will be used
                for tasks given to theWorkGroup in addition to those 
                given in the iprange
        port-> port to be used for communication with the workers 
        
        If both iprange and workers are empty or none, NoWorkersError 
        will be raised
        """
        self.controlls=Manager().list(range(10)) #Will be used for communication 
        self.controlls[_CNT_WORKERS]=[]          #between the mainloops
        if iprange:                             
            for i in parseIPRange(iprange):     #parse the iprange if given
                self.controlls[_CNT_WORKERS]+=[Worker((i, port)),]
        
        if workers:     #Use the workers in the workers paramerer if given
            for i in workers:
                if i.testConnection():
                    self.workers.append(i)
        if not (iprange or workers):        #Cant work without workers
            raise NoWorkersError("No workers given")
        self.queue=Queue()      #Will be used to give orders to the mainloop
    
    def mainloop(self):
        """
        Run the event loop, this should be started before doing any real work
        """
        self._mainloocontroll=Process(target=_mainloopControll, 
                                      args=(self.queue, self.controlls))
        self._mainloopreceiver=Process(target=_mainloopReceiver, 
                                       args=(self.queue, self.controlls))
        self._mainloocontroll.daemon=True
        self._mainloopreceiver.daemon=True
        self._mainloocontroll.start()
        self._mainloopreceiver.start()
    
   
    
    
            
            
