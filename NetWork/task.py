"""

When a task is submited to the workgroup, you get a :py:class:`TaskHandler` object
that can be used to control the running task and receive information about
its state.

"""
import marshal
from types import FunctionType
from .request import sendRequest, sendRequestWithResponse
from .cntcodes import *
from .workerprocess import WorkerProcess

CMD_SUBMIT_TASK = b"TSK"
CMD_TERMINATE_TASK = b"TRM"
CMD_GET_RESULT = b"RSL"
CMD_TASK_RUNNING = b"TRN"
CMD_GET_EXCEPTION = b"EXC"
CMD_CHECK_EXCEPTION = b"EXR"

tasks = {-1: None}


class Task:
    #A class used to hold a task given to the workgroup

    def __init__(self, target=None, args=(), kwargs={}, id=None):
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.id = id

    def __getstate__(self):
        state = {"args": self.args, "kwargs": self.kwargs, "id": self.id,
                 "target": marshal.dumps(self.target.__code__)}
        return state

    def __setstate__(self, state):
        try:
            self.args = state["args"]
            self.kwargs = state["kwargs"]
            self.target = FunctionType(code=marshal.loads(state["target"]),
                                       globals=globals())
            self.id = state["id"]
        except ValueError:
            print("Failed to demarshal a function, this probably means that Python versions are different")


class TaskHandler:
    """
    Class used to controll a running task and get information about it.
    A new instance is returned by :py:meth:`Workgroup.submit <NetWork.workgroup.Workgroup.submit>`
    method.
    """

    def __init__(self, id):
        self.id = id

    def result(self):
        """
        Get return value of the submited function that's running in
        this task. 

        :rtype: pickleable object or None
        :return: return value of the function in the task, ``None`` if the task
          hasn't returned.
        """
        return sendRequestWithResponse(CMD_GET_RESULT,
                                       {
                                           "ID": self.id,
                                       })

    def terminate(self):
        """
        Stop this task, kill its process.
        """
        sendRequest(CMD_TERMINATE_TASK,
                    {
                        "ID": self.id
                    })

    def running(self):
        """
        Check if the task is still running.

        :rtype: bool
        :return: ``True`` or ``False`` depending on whether the task is running.
        """
        return sendRequestWithResponse(CMD_TASK_RUNNING,
                                       {
                                           "ID": self.id,
                                       })

    def exception(self):
        """
        Get the exception that the task has raised.

        :rtype: pickleable object or none
        :return: exception that the task has raised, ``None`` if there was
          no exception.
        """
        return sendRequestWithResponse(CMD_GET_EXCEPTION,
                                       {
                                           "ID": self.id,
                                       })

    def exceptionRaised(self):
        """
        Check if the task has raised an exception.

        :rtype: bool
        :return: ``True`` or ``False`` depending on whether the task has raised an
          exception.
        """
        return sendRequestWithResponse(CMD_CHECK_EXCEPTION,
                                       {
                                           "ID": self.id,
                                       })


def submitTaskMaster(request, controls):
    workerId = request["WORKER"]
    task = request["TASK"]
    controls[CNT_WORKERS][workerId].sendRequest(CMD_SUBMIT_TASK, {"TASK": task})


def taskRunningMaster(request, controls):
    taskId = request["ID"]
    workerId = controls[CNT_TASK_EXECUTORS][taskId]
    request.respond(controls[CNT_WORKERS][workerId].sendRequestWithResponse(CMD_TASK_RUNNING,
                                                                            {
                                                                                "ID": taskId
                                                                            }))


def terminateTaskMaster(request, controls):
    taskId = request["ID"]
    workerId = controls[CNT_TASK_EXECUTORS][taskId]
    controls[CNT_WORKERS][workerId].sendRequest(CMD_TERMINATE_TASK,
                                                {
                                                    "ID": taskId
                                                })


def getExceptionMaster(request, controls):
    taskId = request["ID"]
    workerId = controls[CNT_TASK_EXECUTORS][taskId]
    request.respond(controls[CNT_WORKERS][workerId].sendRequestWithResponse(CMD_GET_EXCEPTION,
                                                                            {
                                                                                "ID": taskId
                                                                            }))


def checkExceptionMaster(request, controls):
    taskId = request["ID"]
    workerId = controls[CNT_TASK_EXECUTORS][taskId]
    request.respond(controls[CNT_WORKERS][workerId].sendRequestWithResponse(CMD_CHECK_EXCEPTION,
                                                                            {
                                                                                "ID": taskId
                                                                            }))


def getResultMaster(request, controls):
    taskId = request["ID"]
    workerId = controls[CNT_TASK_EXECUTORS][taskId]
    request.respond(controls[CNT_WORKERS][workerId].sendRequestWithResponse(CMD_GET_RESULT,
                                                                            {
                                                                                "ID": taskId
                                                                            }))


def executeTaskWorker(request):
    newTask = request["TASK"]
    newProcess = WorkerProcess(newTask)
    tasks[newTask.id] = newProcess
    tasks[newTask.id].start()


def getResultWorker(request):
    id = request["ID"]
    result = tasks[id].getResult()
    request.respond(result)


def exceptionRaisedWorker(request):
    id = request["ID"]
    exceptionTest = tasks[id].exceptionRaised()
    request.respond(exceptionTest)


def terminateTaskWorker(request):
    id = request["ID"]
    tasks[id].terminate()


def taskRunningWorker(request):
    id = request["ID"]
    status = tasks[id].running()
    request.respond(status)


def getExceptionWorker(request):
    id = request["ID"]
    exception = tasks[id].getException()
    request.respond(exception)


masterHandlers = {CMD_SUBMIT_TASK: submitTaskMaster, CMD_GET_RESULT: getResultMaster,
                  CMD_CHECK_EXCEPTION: checkExceptionMaster, CMD_TERMINATE_TASK: terminateTaskMaster,
                  CMD_TASK_RUNNING: taskRunningMaster, CMD_GET_EXCEPTION: getExceptionMaster}

workerHandlers = {CMD_SUBMIT_TASK: executeTaskWorker, CMD_GET_RESULT: getResultWorker,
                  CMD_CHECK_EXCEPTION: exceptionRaisedWorker, CMD_TERMINATE_TASK: terminateTaskWorker,
                  CMD_TASK_RUNNING: taskRunningWorker, CMD_GET_EXCEPTION: getExceptionWorker, }


def masterInit(workgroup):
    pass


def workerInit():
    pass