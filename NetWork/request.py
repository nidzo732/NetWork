import pickle
from NetWork import networking

runningOnMaster = False
workgroup = None


class Request:
    #A class used to send commands to the Workgroup.dispatcher thread
    #Used internaly by workgroup, not by user
    def __init__(self, type, contents, requester=-1, socket=None, commqueue=None, overNetwork=True):
        self.contents = contents
        self.requester = requester
        self.socket = socket
        self.type = type
        self.responseSent = False
        self.overNetwork = overNetwork
        self.commqueue = commqueue

    def getContents(self):
        return self.contents

    def getType(self):
        return self.type

    def __setitem__(self, key, value):
        self.contents[key] = value

    def __getitem__(self, key):
        return self.contents[key]

    def __str__(self):
        #used to print request contents for debuging
        s = "NetWork.request.Request object\n"
        s += "Type " + self.type.decode(encoding="ASCII")
        s += " from"
        if self.requester == -1:
            s += " -1 (master)\n"
        else:
            s += " worker #" + str(self.requester) + " (" + str(self.socket.address) + ")\n"
        s += "Request contents:\n"
        for item in self.contents:
            s += str(item) + " : " + str(self.contents[item]) + "\n"
        return s[:-1]   # Strip last newline character

    def close(self):
        if self.socket:
            if not self.responseSent:
                self.respond(b"DEFAULT_RESPONSE")
            self.socket.close()

    def getResponse(self):
        if self.overNetwork:
            return pickle.loads(self.socket.recv())
        else:
            return self.commqueue.get()

    def respond(self, response):
        if self.overNetwork:
            self.responseSent = True
            try:
                self.socket.send(pickle.dumps(response))
            except OSError as error:
                print("Failed to send response to", self.socket.address, error)
        else:
            self.commqueue.put(response)


def setUp(workGroup=None):
    global runningOnMaster, workgroup
    if workGroup:
        workgroup = workGroup
        runningOnMaster = True
    else:
        runningOnMaster = False


def sendRequest(requestType, contents):
    if runningOnMaster:
        workgroup.sendRequest(requestType, contents)
    else:
        request = Request(requestType, contents)
        masterSocket = networking.NWSocket()
        masterSocket.connect(networking.masterAddress)
        masterSocket.send(request.getType() + pickle.dumps(request.getContents()))
        masterSocket.close()


def sendRequestWithResponse(requestType, contents):
    if runningOnMaster:
        return workgroup.sendRequestWithResponse(requestType, contents)
    else:
        request = Request(requestType, contents)
        masterSocket = networking.NWSocket()
        masterSocket.connect(networking.masterAddress)
        masterSocket.send(request.getType() + pickle.dumps(request.getContents()))
        receivedData = masterSocket.recv()
        masterSocket.close()
        return pickle.loads(receivedData)