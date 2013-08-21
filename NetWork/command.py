class Command:
    #A class used to send commands to the Workgroup.dispatcher thread
    #Used internaly by workgroup, not by user
    def __init__(self, contents, requester, socket=None):
        self.contents=contents
        self.requester=requester
        self.socket=socket
    
    def getContents(self):
        return self.contents[3:]
    
    def type(self):
        return self.contents[:3]
    
    def close(self):
        if self.socket:
            self.socket.close()
    
    def respond(self, response):
        self.socket.send(response)