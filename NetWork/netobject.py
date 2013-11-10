from types import FunctionType
import inspect
import marshal
from .cntcodes import CNT_WORKERS

CMD_REGISTER_NETCLASS = b"NCR"
classCount = 0
classDescriptors = {}


class NetObjectInstance:
    attrs=None
    id=None
    def __init__(self, id):
        self.__dict__["attrs"]={}
        self.__dict__["id"]=id

    def __getattr__(self, item):
        try:
            return classDescriptors[self.id][item]
        except KeyError:
            return self.attrs[item]

    def __setattr__(self, key, value):
        if key=="attrs":
            self.__dict__["attrs"]=value
            return
        self.attrs[key]=value

    def __getstate__(self):
        return {"ATT":self.attrs, "ID":self.id}

    def __setstate__(self, state):
        self.__init__(state["ID"])
        self.attrs=state["ATT"]


class NetObject:
    id=None
    methodDict=None
    workgroup=None
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