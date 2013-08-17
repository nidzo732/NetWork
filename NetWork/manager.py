"""
Managers are used to share data between multiple tasks, they can contain multiple
items that can be read and updated by running tasks. All tasks on all computers
share the item, when one task updates the item, another will see the new value
when reading it.

For more info on managers and what they are see `Python documentation page <http://docs.python.org/3.3/library/multiprocessing.html#managers>`_

There are three types of managers in NetWork, the classic :py:class:`NWManager` 
that uses :py:meth:`setItem <NWManager.setItem>` and :py:meth:`getItem <NWManager.getItem>` methods to update and read items, :py:class:`ManagerDict` which beahaves
like a dictionary that contains shared items, and :py:class:`ManagerNamespace` which contains
shared items as variables.
Here are the examples of all types

::

    #Set and get data from a NWManager
    #Prints '5'
    with Workgroup([...]) as w:
        m=w.registerManager()
        m.setItem("some_number", 5)
        print(m.getItem("some_number"))

::

    #Set and get data from a ManagerDict
    #Prints '5'
    with Workgroup([...]) as w:
        m=w.registerManager()
        d=m.dict()
        d["some_number"]=5
        print(d["some_number"])

::
    
    #Set and get data from a Manager
    #Prints '5'
    with Workgroup([...]) as w:
        m=w.registerManager()
        n=m.namespace()
        n.some_number=5
        print(n.some_number)
"""

import pickle
from .networking import NWSocket
from .commcodes import CMD_GET_MANAGER_ITEM, CMD_SET_MANAGER_ITEM, MANAGER_KEYERROR
from multiprocessing import Manager
runningOnMaster=None
masterAddress=None
managers=None
class NWManager:
    """
    The main manager class that manages a collection of shared data between 
    processes on multiple computers. 
    A new instance is usually created by calling :py:meth:`Workgroup.registerManager <NetWork.workgroup.Workgroup.registerManager>`. 
    The data is managed by using :py:meth:`setItem` and :py:meth:`getItem` methods. 
    To get other types of managers use :py:meth:`dict` and :py:meth:`namespace` methods of :py:class:`NWManager`
    """
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
        masterSocket.send(CMD_GET_MANAGER_ITEM+pickle.dumps({"ID":self.id,                                                     "ITEM":item}))
        value=masterSocket.recv()
        masterSocket.close()
        if value==MANAGER_KEYERROR:
            raise KeyError(item)
        else:
            return pickle.loads(value)
    
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
        """
        Get one of the shared data items in the manager. If the item doesn't 
        exist a ``KeyError`` will be raised.
        
        :Parameters:
          item : any variable that can be used as dict key
            a key identifying the desired item
        """
        if runningOnMaster:
            return self.getItemOnMaster(item)
        else:
            return self.getItemOnWorker(item)
    
    def setItem(self, item, value):
        """
        Set one of the shared data items in the manager. If the item doesn't 
        exist it will be created.
        
        :Parameters:
          item : any variable that can be used as dict key
            a key identifying the desired item
          
          value : any pickleable variable
            new value for the item
        """
        if runningOnMaster:
            self.setItemOnMaster(item, value)
        else:
            self.setItemOnWorker(item, value)
    
    def dict(self, initial=None):
        """
        Get a manager that behaves like a dictionary as described above
        
        :Parameters:
          initial : dict
            optional initial values and names for items in the manager
        
        :Return: an instance of :py:class:`ManagerDict`
        """
        
        return ManagerDict(self.id, self.workgroup, initial)
    
    def namespace(self):
        """
        Get a manager that behaves like a namespace as described above
                
        :Return: an instance of :py:class:`ManagerNamespace`
        """
        return ManagerNamespace(self.id, self.workgroup)
    
    def __setstate__(self, state):
        self.id=state["id"]
        self.workgroup=state["workgroup"]
    
    def __getstate__(self):
        return {"id":self.id, "workgroup":None}

class ManagerDict(NWManager):
    """
    A class that inherits :py:class:`NWManager` but adds :py:meth:`__getitem__` and 
    :py:meth:`__setitem__` methods that enable it to behave like a dictionary
    which might be more comfortable than using :py:meth:`getItem <NWManager.getItem>` and 
    :py:meth:`setItem <NWManager.setItem>` methods of the :py:class:`NWManager`.
    """
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
    """A class that inherits :py:class:`NWManager` but adds :py:meth:`__getattr__` 
    and :py:meth:`__setattr__` methods that enable it to behave like an 
    object containing shared variables which might be more comfortable
    than using :py:meth:`getItem <NWManager.getItem>` and 
    :py:meth:`setItem <NWManager.setItem>` methods of the :py:class:`NWManager`.
    """
    def __init__(self, id, workgroup):
        self.id=id
        self.workgroup=workgroup
    
    def __getattr__(self, key):
        return self.getItem(key)
    
    def __setattr__(self, key, value):
        if key=="id" or key=="workgroup":
            self.__dict__[key]=value
        else:
            self.setItem(key, value)

def setManagerItem(request, controlls, commqueue):
    contents=pickle.loads(request.getContents())
    managers[contents["ID"]][contents["ITEM"]]=contents["VALUE"]

def getManagerItem(request, controlls, commqueue):
    contents=pickle.loads(request.getContents())
    try:
        value=pickle.dumps(managers[contents["ID"]][contents["ITEM"]])
    except KeyError:
        value=MANAGER_KEYERROR
    request.respond(value)