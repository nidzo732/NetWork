from multiprocessing import Process, Manager
from .task import Task

CNT_DONE=1
CNT_RETURN=2
CNT_EXCEPTION_RAISED=3
CNT_EXCEPTION=4
CNT_RUNNING=5
class WorkerProcess:
    def __init__(self, marshaledTask, globalVariables=None):
        self.manager=Manager().list(range(20))
        self.manager[CNT_DONE]=False
        self.manager[CNT_RETURN]=None
        self.manager[CNT_EXCEPTION_RAISED]=False
        self.manager[CNT_EXCEPTION]=None
        self.manager[CNT_RUNNING]=False
        self.process=Process(target=WorkerProcess.runner, 
                             args=(marshaledTask, self.manager, globalVariables))
    
    def start(self):
        self.manager[CNT_RUNNING]=True
        self.process.start()
    
    def getResult(self):
        return self.manager[CNT_RETURN]
    
    def running(self):
        return self.manager[CNT_RUNNING]
    
    def done(self):
        return self.manager[CNT_DONE]
    
    def exceptionRaised(self):  
        return self.manager[CNT_EXCEPTION_RAISED]
    
    def getException(self):
        return self.manager[CNT_EXCEPTION]
    
    def terminate(self):
        if self.manager[CNT_RUNNING]:
            self.process.terminate()
            self.manager[CNT_RUNNING]=False
    
    def join(self):
        if self.manager[CNT_RUNNING]:
            self.process.join()
    
    @staticmethod
    def runner(marshaledTask, manager, globalVariables):
        task=Task(marshaled=marshaledTask, globalVariables=globalVariables)
        returnValue=None
        try:
            returnValue=task.target(*task.args, **task.kwargs)
        except (BaseException, Exception) as exception:
            manager[CNT_EXCEPTION_RAISED]=True
            manager[CNT_EXCEPTION]=exception
        finally:
            manager[CNT_RETURN]=returnValue
            manager[CNT_DONE]=True
            manager[CNT_RUNNING]=False
            return 0