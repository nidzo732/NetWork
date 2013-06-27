workerManager=None

class WorkerEvent:
    def __init__(self, eventId, workerId):
        self.eventId=eventId
        self.workerId=workerId
    
    def wait(self):
        pass
    
    def set(self):
        pass

class MasterEvent:
    def __init__(self, eventId, workerId, workgroup):    
        self.eventId=eventId
        self.workerId=workerId
        self.workgroup=workgroup
    
    def wait(self):
        pass
    
    def set(self):
        pass