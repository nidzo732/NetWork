import marshal
import pickle
from types import FunctionType
#import .handlers
class Task:
    
    def __init__(self, target=None, args=(), kwargs={}, id=None, marshaled=None):
        if marshaled:
            self.unmarshal(marshaled, globs=globs)
        else:
            self.target=target
            self.target
            self.args=args
            self.kwargs=kwargs
            self.id=id



    def marshal(self):
        marshaledTask=b""
        
        marshaledTarget=marshal.dumps(self.target.__code__)
        targetLength=str(len(marshaledTarget)).encode(encoding="ASCII")
        marshaledTask+=targetLength
        marshaledTask+=b"TRG"
        marshaledTask+=marshaledTarget
        
        marshaledArgs=pickle.dumps(self.args)
        argsLength=str(len(marshaledArgs)).encode(encoding="ASCII")
        marshaledTask+=argsLength
        marshaledTask+=b"ARG"
        marshaledTask+=marshaledArgs
        
        marshaledKwargs=pickle.dumps(self.kwargs)
        kwargsLength=str(len(marshaledKwargs)).encode(encoding="ASCII")
        marshaledTask+=kwargsLength
        marshaledTask+=b"KWA"
        marshaledTask+=marshaledKwargs
        
        marshaledTask+=str(self.id).encode(encoding="ASCII")
        
        return marshaledTask


    
    def unmarshal(self, marshaledTask):
        targetLength=int(marshaledTask[:marshaledTask.find(b"TRG")])
        marshaledTask=marshaledTask[marshaledTask.find(b"TRG")+3:]
        marshaledTarget=marshaledTask[:targetLength]
        
        marshaledTask=marshaledTask[targetLength:]
        argsLength=int(marshaledTask[:marshaledTask.find(b"ARG")])
        marshaledTask=marshaledTask[marshaledTask.find(b"ARG")+3:]
        marshaledArgs=marshaledTask[:argsLength]
        marshaledTask=marshaledTask[argsLength:]
        
        kwargsLength=int(marshaledTask[:marshaledTask.find(b"KWA")])
        marshaledTask=marshaledTask[marshaledTask.find(b"KWA")+3:]
        marshaledKwargs=marshaledTask[:kwargsLength]
        
        marshaledTask=marshaledTask[kwargsLength:]
        
        self.kwargs=pickle.loads(marshaledKwargs)
        self.args=pickle.loads(marshaledArgs)
        self.target=FunctionType(code=marshal.loads(marshaledTarget), 
                                 globals=globals())
        self.id=int(marshaledTask)

class TaskHandler:
    
    def __init__(self, id, workgroup, worker):
        self.workgroup=workgroup
        self.id=id
        self.worker=worker
    
    def result(self):
        try:
            return self.workgroup.getResult(self.id, self.worker)
        except DeadWorkerError:
            newHandler=self.workgroup.fixDeadWorker(self.id, self.worker)
            self.id=newHandler.id
            self.worker=newHandler.worker
            return self.result()
    
    def terminate(self):
        try:
            return self.workgroup.cancelTask(self.id, self.worker)
        except DeadWorkerError:
            newHandler=self.workgroup.fixDeadWorker(self.id, self.worker)
            self.id=newHandler.id
            self.worker=newHandler.worker
            return self.cancel()
        
    def running(self):
        try:
            return self.workgroup.taskRunning(self.id, self.worker)
        except DeadWorkerError:
            newHandler=self.workgroup.fixDeadWorker(self.id, self.worker)
            self.id=newHandler.id
            self.worker=newHandler.worker
            return self.running()
        
    
    def exception(self):
        try:
            return self.workgroup.getException(self.id, self.worker)
        except DeadWorkerError:
            newHandler=self.workgroup.fixDeadWorker(self.id, self.worker)
            self.id=newHandler.id
            self.worker=newHandler.worker
            return self.exception()
    
    def exceptionRaised(self):
        try:
            return self.workgroup.exceptionRaised(self.id, self.worker)
        except DeadWorkerError:
            newHandler=self.workgroup.fixDeadWorker(self.id, self.worker)
            self.id=newHandler.id
            self.worker=newHandler.worker
            return self.exception()