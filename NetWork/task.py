import marshal
from types import FunctionType
#import .handlers
class Task:
    
    def __init__(self, target=None, args=(), kwargs={}):
        self.target=target
        self.target
        self.args=args
        self.kwargs=kwargs
    
    def marshal(self):
        marshaledTask=b""
        marshaledTarget=marshal.dumps(self.target.__code__)
        targetLength=str(len(marshaledTarget)).encode(encoding="ASCII")
        marshaledTask+=targetLength
        marshaledTask+=b"TRG"
        marshaledTask+=marshaledTarget
        marshaledArgs=marshal.dumps(self.args)
        argsLength=str(len(marshaledArgs)).encode(encoding="ASCII")
        marshaledTask+=argsLength
        marshaledTask+=b"ARG"
        marshaledTask+=marshaledArgs
        marshaledKwargs=marshal.dumps(self.kwargs)
        kwargsLength=str(len(marshaledKwargs)).encode(encoding="ASCII")
        marshaledTask+=kwargsLength
        marshaledTask+=b"KWA"
        marshaledTask+=marshaledKwargs
        return marshaledTask
    
    def unmarshal(self, marshaledTask):
        targetLength=int(marshaledTask[:marshaledTask.find(b"TRG")])
        marshaledTask=marshaledTask[marshaledTask.find(b"TRG")+3:]
        marshaledTarget=marshaledTask[:targetLength]
        marshaledTask=marshaledTask[targetLength:]
        argsLength=int(marshaledTask[:marshaledTask.find(b"ARG")])
        marshaledTask=marshaledTask[marshaledTask.find(b"ARG")+3:]
        marshaledArgs=marshaledTask[:argsLength]
        marshaledTask=marshaledTask[argsLength:]
        kwargsLength=int(marshaledTask[:marshaledTask.find(b"KWA")])
        marshaledTask=marshaledTask[marshaledTask.find(b"KWA")+3:]
        marshaledKwargs=marshaledTask[:kwargsLength]
        self.kwargs=marshal.loads(marshaledKwargs)
        self.args=marshal.loads(marshaledArgs)
        self.target=FunctionType(code=marshal.loads(marshaledTarget), globals=globals())
        
        