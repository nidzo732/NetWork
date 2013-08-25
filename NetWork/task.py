"""

When a task is submited to the workgroup, you get a :py:class:`TaskHandler` object
that can be used to control the running task and receive information about
its state.

"""
import marshal
import pickle
from types import FunctionType
#import .handlers

class Task:
    #A class used to hold a task given to the workgroup
    
    def __init__(self, target=None, args=(), kwargs={}, id=None, marshaled=None, 
                 globalVariables=None):
        if marshaled:
            self.unmarshal(marshaled, globalVariables)
        else:
            self.target=target
            self.target
            self.args=args
            self.kwargs=kwargs
            self.id=id
    
    def __getstate__(self):
        state={"ARGS":self.args, "KWARGS":self.kwargs}
        state["TARGET"]=marshal.dumps(self.target.__code__)
    
    def __setstate__(self, state):
        self.args=state["ARGS"]
        self.kwargs=state["KWARGS"]
        self.target=FunctionType(code=marshal.loads(state["TARGET"]), 
                                 globals=globals())


class TaskHandler:
    """
    Class used to controll a running task and get information about it.
    A new instance is returned by :py:meth:`Workgroup.submit <NetWork.workgroup.Workgroup.submit>`
    method.
    """
    
    def __init__(self, id, workgroup, worker):
        self.workgroup=workgroup
        self.id=id
        self.worker=worker
    
    def result(self):
        """
        Get return value of the submited function that's running in
        this task. 
        
        :Return: return value of the function in the task, ``None`` if the task
          hasn't returned.
        """
        try:
            return self.workgroup.getResult(self.id, self.worker)
        except DeadWorkerError:
            newHandler=self.workgroup.fixDeadWorker(self.id, self.worker)
            self.id=newHandler.id
            self.worker=newHandler.worker
            return self.result()
    
    def terminate(self):
        """
        Stop this task, kill its process.
        """
        try:
            return self.workgroup.cancelTask(self.id, self.worker)
        except DeadWorkerError:
            newHandler=self.workgroup.fixDeadWorker(self.id, self.worker)
            self.id=newHandler.id
            self.worker=newHandler.worker
            return self.cancel()
        
    def running(self):
        """
        Check if the task is still running.
        
        :Return: ``True`` or ``False`` depending on whether the task is running.
        """
        try:
            return self.workgroup.taskRunning(self.id, self.worker)
        except DeadWorkerError:
            newHandler=self.workgroup.fixDeadWorker(self.id, self.worker)
            self.id=newHandler.id
            self.worker=newHandler.worker
            return self.running()
        
    
    def exception(self):
        """
        Get the exception that the task has raised.
        
        :Return: exception that the task has raised, ``None`` if there was
          no exception.
        """
        try:
            return self.workgroup.getException(self.id, self.worker)
        except DeadWorkerError:
            newHandler=self.workgroup.fixDeadWorker(self.id, self.worker)
            self.id=newHandler.id
            self.worker=newHandler.worker
            return self.exception()
    
    def exceptionRaised(self):
        """
        Check if the task has raised an exception.
        
        :Return: ``True`` or ``False`` depending on whether the task has raised an
          exception.
        """
        
        try:
            return self.workgroup.exceptionRaised(self.id, self.worker)
        except DeadWorkerError:
            newHandler=self.workgroup.fixDeadWorker(self.id, self.worker)
            self.id=newHandler.id
            self.worker=newHandler.worker
            return self.exception()