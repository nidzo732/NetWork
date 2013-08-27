class Request:
    #A class used to send commands to the Workgroup.dispatcher thread
    #Used internaly by workgroup, not by user
    def __init__(self, type, contents, requester=-1, socket=None):
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
    
    def __str__(self):
        #used to print request contents for debuging
        s="NetWork.request.Request object\n"
        s+="Type "+self.type.decode(encoding="ASCII")
        s+=" from"
        if self.requester==-1:
            s+=" -1 (master)\n"
        else:
            s+=" worker #"+str(self.requester)+" ("+str(self.socket.address)+")\n"
        s+="Request contents:\n"
        for item in self.contents:
            s+=str(item)+" : "+str(self.contents[item])+"\n"
        return s[:-1]   #Strip last newline character
    
    def close(self):
        if self.socket:
            self.socket.close()
    
    def respond(self, response):
        try:
            self.socket.send(response)
        except OSError as error:
            print("Failed to send response to", self.socket.address, error)