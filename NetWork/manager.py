import pickle
from .networking import NWSocket
from .commcodes import CMD_GET_MANAGER_ITEM, CMD_SET_MANAGER_ITEM
from multiprocessing import Manager
runningOnMaster=None
masterAddress=None
managers=None
class NWManager:
    def __init__(self, id, workgroup):
        self.id=id
        self.workgroup=workgroup
        if runningOnMaster:
            managers[self.id]=Manager().dict()
    
    def getItemOnMaster(self, item):
        return managers[self.id][item]
    
    def getItemOnWorker(self, item):
        masterSocket=NWSocket()
        masterSocket.connect(masterAddress)
        masterSocket.send(CMD_GET_MANAGER_ITEM+pickle.dumps({"ID":self.id,
                                                             "ITEM":self.item}))
        value=pickle.loads(masterSocket.recv())
        masterSocket.close()
        return value
    
    def setItemOnMaster(self, item, value):
        self.workgroup.setManagerItem(self.id, item, value)
    
    def setItemOnWorker(self, item, value):
        masterSocket=NWSocket()
        masterSocket.connect(masterAddress)
        masterSocket.send(CMD_SET_MANAGER_ITEM+pickle.dumps({"ID":self.id,
                                                             "ITEM":item,
                                                             "VALUE":value}))
        masterSocket.close()
    
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
    
    def dict(self, initial=None):
        return ManagerDict(self.id, self.workgroup, initial)
    
    def namespace(self):
        return ManagerNamespace(self.id, self.workgroup)

class ManagerDict(NWManager):
    def __init__(self, id, workgroup, initial=None):
        self.id=id
        self.workgroup=workgroup
        if initial:
            for key in initial:
                self.setItem(key, initial[key])
    
    def __getitem__(self, key):
        return self.getItem(key)
    
    def __setitem__(self, key, value):
        self.setItem(key, value)

class ManagerNamespace(NWManager):
    def __init__(self, id, workgroup):
        self.id=id
        self.workgroup=workgroup
    
    def __getattr__(self, key):
        return self.getItem(key)
    
    def __setattr(self, key, value):
        self.setItem(key, value)

def setManagerItem(request, controlls, commqueue):
    contents=pickle.loads(request.getContents())
    managers[contents["id"]][contents["item"]]=contents["value"]

def getManagerItem(request, controlls, commqueue):
    contents=pickle.loads(request.getContents())
    value=pickle.dumps(managers[contents["id"]][contents["item"]])
    request.respond(value)