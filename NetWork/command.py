class Request:
    #A class used to send commands to the Workgroup.dispatcher thread
    #Used internaly by workgroup, not by user
    def __init__(self, type, contents, requester, socket=None):
        self.contents=contents
        self.requester=requester
        self.socket=socket
        self.type=type
    
    def getContents(self):
        return self.contents
    
    def getType(self):
        return self.type
    
    def __setitem__(self, key, value):
        self.contents[key]=value
    
    def __getitem__(self, key):
        return self.contents[key]
    
    def close(self):
        if self.socket:
            self.socket.close()
    
    def respond(self, response):
        try:
            self.socket.send(response)
        except OSError as error:
            print("Failed to send response to", self.socket.address, error)