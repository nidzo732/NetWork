"""
Module that implements a WorkProcess class. 
This class will be used as a wrapper for real long running
rocesses that will be created on the worker computers

Created on Jan 8, 2013
"""

from multiprocessing import Process, Manager, Event


#Values that describe the status of the running process
#Possible values of the WorkProcess.workStatus[_WS_RUNSTATE]
#Internal use only

_RS_STOPPED=0 
_RS_RUNNING=1
_RS_FINISHED=2


#Positions in the WorkProcess.WorkStatus list that comunicates
#with the running process
#Internal use only

_WS_RUNSTATE=0  #Process status - running, finished, stopped
_WS_RETVALUE=1  #Proceess return value
_WS_EXCEPTION_RAISED=2  #Whether an exception was raised 
_WS_EXCEPTION=3 #Exception raised by the process

#Exceptions raised by WorkProcess methods
class AlreadyRunningError(Exception): pass
    
class WorkProcess:
    """
    Wrapper for the real work that is being done on remote computers
    """
    
    def __init__(self, target, args=None, kwargs=None):
        """
        Create a new WorkProcess
        target -> the function to run
        args,kwargs -> function arguments and keyword arguments
        """
        self.workStatus=Manager().list(range(4))    
        self.workStatus[_WS_RUNSTATE]=_RS_STOPPED
        if not args:
            self.args=tuple()
        else:
            self.args=args
        if not kwargs:
            self.kwargs={}
        else:
            self.kwargs=kwargs
        self.target=target
        self.finishedEvent=Event()  #Notifies when the process finishes
        self.worker=Process(target=self.runner,
                            args=(self.target, self.workStatus, 
                                  self.finishedEvent, 
                                  self.args, self.kwargs,))
        self.worker.daemon=True     #Manager breaks otherwise
        
    def start(self):
        """
        Run the process
        If running multiple times do a .reset before each run
        """
        if not self.workStatus[_WS_RUNSTATE]==_RS_STOPPED: #Can't run twice
            raise AlreadyRunningError("WorkProcess is already running")    
        self.finishedEvent.clear()    
        self.worker.start()
    
    def hasReturned(self):
        """
        Check whether the target function has returned
        """
        return self.workStatus[_WS_RUNSTATE]==_RS_FINISHED
    
    def exceptionRaised(self):
        """
        Check whether the target function has raised an exception
        """
        if not self.hasReturned():
            return False
        return self.workStatus[_WS_EXCEPTION_RAISED]
    
    def getException(self):
        """
        Get the exception that was raised by the target
        """
        if not self.exceptionRaised():
            return None
        return self.workStatus[_WS_EXCEPTION]
    
    def returnValue(self): 
        """
        Get the return value of the target
        """
        if not self.hasReturned():
            return None
        return self.workStatus[_WS_RETVALUE]
    
    def terminate(self):
        """
        Kill the process
        """
        self.worker.terminate()
    
    def waitForFinish(self, timeout=None):
        """
        Wait for the process to finish, waits until timeout
        if set, otherwise waits forever
        """
        self.finishedEvent.wait(timeout)
    
    def reset(self):
        """
        Kill the current process and reset it's state
        Do this if you start the process multiple times
        """
        self._resetProcess()
        self.workStatus[_WS_RUNSTATE]=_RS_STOPPED
        self.finishedEvent.set()        
    
    def __del__(self):
        self.worker.terminate()
    
    def _resetProcess(self):
        if self.worker.is_alive():
            self.worker.terminate()
        self.worker.join()
        self.worker=Process(target=self.runner, 
                            args=(self.target, self.workStatus, 
                                  self.finishedEvent, self.args, 
                                  self.kwargs,)
                            )
        self.worker.daemon=True
    
    def __getattr__(self, key):
        return self.worker.__dict__[key]
    
    @staticmethod
    def runner(target, manager, finish_event, args=None, kwargs=None):
        """
        Function that actually runs the target
        Internal use only
        """
        try:
            rv=target(*args, **kwargs)
            manager[_WS_RETVALUE]=rv
            manager[_WS_EXCEPTION_RAISED]=False        
        except(Exception) as exception:
            manager[_WS_EXCEPTION_RAISED]=True
            manager[_WS_EXCEPTION]=exception
        finally:
            manager[_WS_RUNSTATE]=_RS_FINISHED
            finish_event.set()
            
    