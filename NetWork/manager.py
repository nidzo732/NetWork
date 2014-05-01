"""
Managers are used to share data between multiple tasks, they can contain multiple
items that can be read and updated by running tasks. All tasks on all computers
share the item, when one task updates the item, another will see the new value
when reading it.

For more info on managers and what they are see `Python documentation page
<http://docs.python.org/3.3/library/multiprocessing.html#managers>`_

There are three types of managers in NetWork, the classic :py:class:`NWManager` 
that uses :py:meth:`setItem <NWManager.setItem>` and :py:meth:`getItem <NWManager.getItem>`
methods to update and read items, :py:class:`ManagerDict` which beahaves
like a dictionary that contains shared items, and :py:class:`ManagerNamespace` which contains
shared items as variables.
Here are the examples of all types

::

    #Set and get data from a NWManager
    #Prints '5'
    from NetWork import Manager
    with Workgroup([...]) as w:
        m=Manager(w)
        m.setItem("some_number", 5)
        print(m.getItem("some_number"))

::

    #Set and get data from a ManagerDict
    #Prints '5'
    from NetWork import Manager
    with Workgroup([...]) as w:
        m=Manager(w)
        d=m.dict()
        d["some_number"]=5
        print(d["some_number"])

::
    
    #Set and get data from a Manager
    #Prints '5'
    from NetWork import Manager
    with Workgroup([...]) as w:
        m=Manager(w)
        n=m.namespace()
        n.some_number=5
        print(n.some_number)
"""

from multiprocessing import Manager

from .request import sendRequest, sendRequestWithResponse


CMD_REGISTER_MANAGER = b"MNR"
CMD_SET_MANAGER_ITEM = b"MNS"
CMD_GET_MANAGER_ITEM = b"MNG"
CMD_GET_MANAGER_KEYS = b"MNK"
CMD_CHECK_IF_MANAGER_CONTAINS = b"CON"
CMD_GET_MANAGER_LENGTH = b"LGH"

MANAGER_KEYERROR = b"KERR"
CNT_MANAGER_COUNT = "MANAGER_COUNT"

runningOnMaster = None
masterAddress = None
managers = None


def masterInit(workgroup):
    global runningOnMaster, managers
    runningOnMaster = True
    managers = {-1: None}
    workgroup.controls[CNT_MANAGER_COUNT] = 0


def workerInit():
    global runningOnMaster
    runningOnMaster = False


class NWManager:
    """
    The main manager class that manages a collection of shared data between 
    processes on multiple computers. 
    The data is managed by using :py:meth:`setItem` and :py:meth:`getItem` methods.
    To get other types of managers use :py:meth:`dict` and :py:meth:`namespace` methods of :py:class:`NWManager`

    :type workgroup: NetWork.workgroup.Workgroup
    :param workgroup: workgroup that will be using this Manager
    """

    def __init__(self, workgroup):
        self.workgroup = workgroup
        self.workgroup.controls[CNT_MANAGER_COUNT] += 1
        self.id = self.workgroup.controls[CNT_MANAGER_COUNT]
        if runningOnMaster:
            managers[self.id] = Manager().dict()

    def getItemOnMaster(self, item):
        return managers[self.id][item]

    def getItemOnWorker(self, item):
        value = sendRequestWithResponse(CMD_GET_MANAGER_ITEM,
                                        {
                                            "ID": self.id,
                                            "ITEM": item
                                        })

        if value == MANAGER_KEYERROR:
            raise KeyError(item)
        else:
            return value

    def getItem(self, item):
        """
        Get one of the shared data items in the manager. If the item doesn't 
        exist a ``KeyError`` will be raised.

        :type item: any pickleable object that can be used as dict key
        :param item: a key identifying the desired item

        :return: item in the manager that has the given key
        """
        if runningOnMaster:
            return self.getItemOnMaster(item)
        else:
            return self.getItemOnWorker(item)

    def setItem(self, item, value):
        """
        Set one of the shared data items in the manager. If the item doesn't 
        exist it will be created.
        
        :type item: any pickleable object that can be used as dict key
        :param item:    a key identifying the desired item

        :type value: any pickleable object
        :param value: new value for the item
        """
        sendRequest(CMD_SET_MANAGER_ITEM,
                    {
                        "ID": self.id,
                        "ITEM": item,
                        "VALUE": value
                    })

    def dict(self, initial=None):
        """
        Get a manager that behaves like a dictionary as described above
        
        :type initial: dict
        :param initial: optional initial values and names for items in the manager

        :rtype: :py:class:`ManagerDict <NetWork.manager.ManagerDict>`
        :return: a manager that behaves like a dictionary
        """

        return ManagerDict(self.id, self.workgroup, initial)

    def namespace(self):
        """
        Get a manager that behaves like a namespace as described above

        :rtype: :py:class:`ManagerNamespace <NetWork.manager.ManagerNamespace>`
        :return: a manager that behaves like a namespace
        """
        return ManagerNamespace(self.id, self.workgroup)


    def __setstate__(self, state):
        self.id = state["id"]
        self.workgroup = state["workgroup"]

    def __getstate__(self):
        return {"id": self.id, "workgroup": None}


class ManagerDict(NWManager):
    """
    A class that inherits :py:class:`NWManager` but adds :py:meth:`__getitem__` and 
    :py:meth:`__setitem__` methods that enable it to behave like a dictionary
    which might be more comfortable than using :py:meth:`getItem <NWManager.getItem>` and 
    :py:meth:`setItem <NWManager.setItem>` methods of the :py:class:`NWManager`.
    """

    def __init__(self, id, workgroup, initial=None):
        self.id = id
        self.workgroup = workgroup
        if initial:
            for key in initial:
                self.setItem(key, initial[key])

    def __contains__(self, item):
        return sendRequestWithResponse(CMD_CHECK_IF_MANAGER_CONTAINS,
                                       {
                                           "ID": self.id,
                                           "ITEM": item
                                       })

    def __len__(self):
        return sendRequestWithResponse(CMD_GET_MANAGER_LENGTH,
                                       {
                                           "ID": self.id
                                       })

    def keys(self):
        return sendRequestWithResponse(CMD_GET_MANAGER_KEYS,
                                       {
                                           "ID":self.id
                                       })
    def __iter__(self):
        return iter(self.keys())

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
        self.id = id
        self.workgroup = workgroup

    def __getattr__(self, key):
        return self.getItem(key)

    def __setattr__(self, key, value):
        if key == "id" or key == "workgroup":
            self.__dict__[key] = value
        else:
            self.setItem(key, value)


def setManagerItemMaster(request, controlls):
    #A handler used by Workgroup.dispatcher
    managers[request["ID"]][request["ITEM"]] = request["VALUE"]


def getManagerItemMaster(request, controlls):
    #A handler used by Workgroup.dispatcher
    try:
        value = managers[request["ID"]][request["ITEM"]]
    except KeyError:
        value = MANAGER_KEYERROR
    request.respond(value)


def getManagerKeys(request, controlls):
    request.respond(managers[request["ID"]].keys())


def checkIfManagerContains(request, controlls):
    request.respond(request["ITEM"] in managers[request["ID"]])


def getManagerLength(request, controlls):
    request.respond(len(managers[request["ID"]]))


masterHandlers = {CMD_SET_MANAGER_ITEM: setManagerItemMaster, CMD_GET_MANAGER_ITEM: getManagerItemMaster,
                  CMD_GET_MANAGER_LENGTH: getManagerLength, CMD_CHECK_IF_MANAGER_CONTAINS: checkIfManagerContains,
                  CMD_GET_MANAGER_KEYS: getManagerKeys,}
workerHandlers = {}