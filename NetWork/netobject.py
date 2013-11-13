"""
One of the problems caused by the networked architecture is the inability to use
non-builtin objects. The objects get pickled on the master but they can't be unpickled on
the workers because they aren't defined there.
The NetObject class solves this problem, it wraps custom classes and enables them to be used
in the tasks.
To use class on the workgroup create a new wrapper :py:class:`NetObject`, after that you use that wrapper
to create new instances of that class that can be passed freely around the workgroup.

.. code-block:: python

    from NetWork import Workgroup, NetObject

    class MyClass:

        def __init__(self,......):
            some code, blah, blah
            .....
            .....

        def doStuff(self,.......):
            some other code, blah, blah
            .....
            .....

    def someFunction(someObject):
        return someObject.doStuff(......)

    with Workgroup(workerList....) as w:
        MyClassWrapped=NetObject(MyClass, w)
        myInstance=MyClassWraped(......)
        task1=w.submit(target=someFunction, args=(myInstance))

Without the wrapping part, an exception would get raised in task1 about failed unpickling.
"""
from types import FunctionType
import inspect
import marshal
from .cntcodes import CNT_WORKERS

CMD_REGISTER_NETCLASS = b"NCR"
classCount = 0
classDescriptors = {}


class MethodWrapper:
    #Methods get "unbound" when a class is registered, as a result the user
    #would need to give the self argument explicitly when calling the method. This wrapper
    #class prevents such behavior by adding the self argument before calling the method

    def __init__(self, method, owner):
        self.method = method
        self.owner = owner

    def __call__(self, *args, **kwargs):
        return self.method(self.owner, *args, **kwargs)


class NetObjectInstance:
    #This class is created as an instance of any registered NetObject
    #It has an id that points to an apropriate descriptor in classDescriptors
    #and a dict called attrs that holds values of instance attributes
    attrs = None
    classId = None

    def __init__(self, classId):
        self.__dict__["attrs"] = {}
        self.__dict__["classId"] = classId

    def __getattr__(self, item):
        try:
            attribute = classDescriptors[self.classId][item]
        except KeyError:
            attribute = self.attrs[item]
        if inspect.isfunction(attribute):
            return MethodWrapper(attribute, self)
        else:
            return attribute

    def __setattr__(self, key, value):
        if key == "attrs":
            self.__dict__["attrs"] = value
            return
        self.attrs[key] = value

    def __getstate__(self):
        return {"ATT": self.attrs, "ID": self.classId}

    def __setstate__(self, state):
        self.__init__(state["ID"])
        self.attrs = state["ATT"]


class NetObject:
    """
    Wrap the class to be used by the workgroup.

    Don't use the original class to create instances, use this object instead.

    :type base: class
    :param base: The class to be wrapped
    :type workgroup: NetWork.workgroup.Workgroup
    :param workgroup: Workgroup that will be using this class
    """
    id = None
    methodDict = None
    workgroup = None

    def __init__(self, base, workgroup):
        methodList = inspect.getmembers(base, inspect.isfunction)
        self.methodDict = {}
        for method in methodList:
            self.methodDict[method[0]] = method[1]
        global classCount
        classCount += 1
        self.id = classCount
        classDescriptors[classCount] = self.methodDict
        self.workgroup = workgroup
        self.workgroup.sendRequest(CMD_REGISTER_NETCLASS,
                                   {"CLS": self})

    def __call__(self, *args, **kwargs):
        """
        Create a new instance of the wrapped class. All arguments will be passed
        to its` :py:meth:`__init__`.

        :return: instance of the wrapped class
        """
        newObject = NetObjectInstance(self.id)
        classDescriptors[self.id]["__init__"](newObject, *args, **kwargs)
        return newObject

    def __getstate__(self):
        pickledMethods = {}
        for method in self.methodDict:
            pickledMethods[method] = marshal.dumps(self.methodDict[method].__code__)
        pickledMethods["ID"] = self.id
        return pickledMethods

    def __setstate__(self, state):
        self.id = state["ID"]
        state.pop("ID")
        self.methodDict = {}
        for method in state:
            self.methodDict[method] = FunctionType(code=marshal.loads(state[method]), globals=globals())
        if not self.id in classDescriptors:
            classDescriptors[self.id] = self.methodDict


def masterInit(workgroup):
    pass


def workerInit():
    pass


def registerClassMaster(request, controlls, commqueue):
    for worker in controlls[CNT_WORKERS]:
        worker.sendRequest(CMD_REGISTER_NETCLASS, {"CLS": request["CLS"]})


def registerClassWorker(request):
    classDescriptors[request["CLS"].id] = request["CLS"].methodDict


masterHandlers = {CMD_REGISTER_NETCLASS: registerClassMaster}
workerHandlers = {CMD_REGISTER_NETCLASS: registerClassWorker}