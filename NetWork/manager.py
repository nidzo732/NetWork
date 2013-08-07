runningOnMaster=None
class NWManager:
    def __init__(self, id, workgroup):
        self.id=id
        self.workgroup=workgroup
    
    def getItemOnMaster(self, item):
        pass
    
    def getItemOnWorker(self, item):
        pass
    
    def setItemOnMaster(self, item, value):
        pass
    
    def setItemOnWorker(self, item, value):
        pass
    
    def getItem(self, item):
        if runningOnMaster:
            return self.getItemOnMaster(item)
        else:
            return self.getItemOnWorker(item)
    
    def setItem(self, item, value):
        if runningOnMaster:
            self.setItemOnMaster(item, value)
        else:
            self.setItemOnWorker(item, value)