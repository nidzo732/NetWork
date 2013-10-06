"""
This module implements the WorkerProcess class that is used on worker computers
to represent running tasks it also implements methods to control that task
and get information about it.
"""
from multiprocessing import Process, Manager

CNT_DONE = 1
CNT_RETURN = 2
CNT_EXCEPTION_RAISED = 3
CNT_EXCEPTION = 4
CNT_RUNNING = 5


class WorkerProcess:
    #Class to hold and control running task
    def __init__(self, task):
        self.manager = Manager().list(range(20))
        self.manager[CNT_DONE] = False
        self.manager[CNT_RETURN] = None
        self.manager[CNT_EXCEPTION_RAISED] = False
        self.manager[CNT_EXCEPTION] = None
        self.manager[CNT_RUNNING] = False
        self.process = Process(target=WorkerProcess.runner,
                               args=(task, self.manager))

    def start(self):
        self.manager[CNT_RUNNING] = True
        self.process.start()

    def getResult(self):
        return self.manager[CNT_RETURN]

    def running(self):
        return self.manager[CNT_RUNNING]

    def done(self):
        return self.manager[CNT_DONE]

    def exceptionRaised(self):
        return self.manager[CNT_EXCEPTION_RAISED]

    def getException(self):
        return self.manager[CNT_EXCEPTION]

    def terminate(self):
        if self.manager[CNT_RUNNING]:
            self.process.terminate()
            self.manager[CNT_RUNNING] = False

    def join(self):
        if self.manager[CNT_RUNNING]:
            self.process.join()

    @staticmethod
    def runner(task, manager):
        #A function that actualy runs the task
        returnValue = None
        try:
            returnValue = task.target(*task.args, **task.kwargs)
        except (BaseException, Exception) as exception:
            manager[CNT_EXCEPTION_RAISED] = True
            manager[CNT_EXCEPTION] = exception
        finally:
            manager[CNT_RETURN] = returnValue
            manager[CNT_DONE] = True
            manager[CNT_RUNNING] = False
            return 0