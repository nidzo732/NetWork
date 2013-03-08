"""
This file implements a worker class that is used to describe
one worker computer

Created on Jan 12, 2013
"""
class WorkerUnavailableError(Exception):pass
from .networking import isAlive

class Worker:   #Not yet implemented
    def __init__(self, addr):
        #print("WORKER CREATED WITH ADDRESS", addr[0],":", addr[1])
        if isAlive(addr)==False:
            raise WorkerUnavailableError("""Worker on address "+addr[0]+"is not
            available for communication""")
        