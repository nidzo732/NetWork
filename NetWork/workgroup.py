"""
This file implements a WorkGroup class. It will define a group of worker
computers, distribute their work and provide communication between them.

Created on Jan 11, 2013
"""

from .parsers import parseIPRange
from .worker import Worker
from multiprocessing import Process, Queue, Manager, Event
import socket
from .networking import getLocalIP, parseRequest

#Positions in the WorkGroup.controlls list that is used for communication between
#the processes
CNT_WORKERS=0
CNT_PORT=1
CNT_SHOULD_STOP=2

CMD_HALT=b"HLT"     #Put this on the queue to stop the _mainloopcontroll

#Exceptions used by workgroup
class NoWorkersError(Exception):pass


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
        self.controlls[CNT_WORKERS]=[]          #between the mainloops
        self.controlls[CNT_PORT]=port
        self.controlls[CNT_SHOULD_STOP]=False
        if iprange:                             
            for i in parseIPRange(iprange):     #parse the iprange if given
                self.controlls[CNT_WORKERS]+=[Worker((i, port)),]
        
        if workers:     #Use the workers in the workers paramerer if given
            for i in workers:
                if i.testConnection():
                    self.controlls[CNT_WORKERS]+=[workers[i]]
        if not (iprange or workers):        #Cant work without workers
            raise NoWorkersError("No workers given")
        self.queue=Queue()      #Will be used to give orders to the mainloop
    
    def mainloop(self):
        """
        Run the event loop, this should be started before doing any real work
        """
        self._mainloopcontroll=Process(target=WorkGroup._mainloopControll, 
                                      args=(self.queue, self.controlls))
        self._mainloopreceiver=Process(target=WorkGroup._mainloopReceiver, 
                                       args=(self.queue, self.controlls))
        self._mainloopcontroll.daemon=True
        self._mainloopreceiver.daemon=True
        self._mainloopcontroll.start()
        self._mainloopreceiver.start()
    
    def halt(self):
        """
        Halt the mainloops
        """
        self.queue.put(CMD_HALT)
        self._mainloopreceiver.join()
        self._mainloopcontroll.join()
    
    def __del__(self):
        if self._mainloopcontroll.is_alive() or self._mainloopreceiver.is_alive():
            self.halt()
    
    #An event loop that will receive the network input from the worker computers
    #and sends it to the comm Queue
    @staticmethod
    def _mainloopReceiver(commqueue, controlls):     #Not yet implemented
        receiverSocket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        receiverSocket.bind((getLocalIP(), controlls[CNT_PORT]))
        receiverSocket.listen(5)
        while True and not controlls[CNT_SHOULD_STOP]:
            commSocket, comAddr=receiverSocket.accept()
            parseRequest(commSocket, commqueue)
        receiverSocket.close()
        

    #An event loop that will receive tasks through the commqueue Queue and act
    #accordingly
    @staticmethod
    def _mainloopControll(commqueue, controlls):     #Not yet implemented
        job=commqueue.get()
        while job!=CMD_HALT:
            print("GOT A JOB", job)
            job=commqueue.get()
        controlls[CNT_SHOULD_STOP]=True