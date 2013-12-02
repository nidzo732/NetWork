"""

When a task is submited to the workgroup, you get a :py:class:`TaskHandler` object
that can be used to control the running task and receive information about
its state.

"""
import marshal
from types import FunctionType


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
        self.args = state["args"]
        self.kwargs = state["kwargs"]
        self.target = FunctionType(code=marshal.loads(state["target"]),
                                   globals=globals())
        self.id = state["id"]


class TaskHandler:
    """
    Class used to controll a running task and get information about it.
    A new instance is returned by :py:meth:`Workgroup.submit <NetWork.workgroup.Workgroup.submit>`
    method.
    """

    def __init__(self, id, workgroup):
        self.workgroup = workgroup
        self.id = id

    def result(self):
        """
        Get return value of the submited function that's running in
        this task. 

        :rtype: pickleable object or None
        :return: return value of the function in the task, ``None`` if the task
          hasn't returned.
        """
        return self.workgroup.getResult(self.id)

    def terminate(self):
        """
        Stop this task, kill its process.
        """
        return self.workgroup.cancelTask(self.id)

    def running(self):
        """
        Check if the task is still running.

        :rtype: bool
        :return: ``True`` or ``False`` depending on whether the task is running.
        """
        return self.workgroup.taskRunning(self.id)

    def exception(self):
        """
        Get the exception that the task has raised.

        :rtype: pickleable object or none
        :return: exception that the task has raised, ``None`` if there was
          no exception.
        """
        return self.workgroup.getException(self.id)

    def exceptionRaised(self):
        """
        Check if the task has raised an exception.

        :rtype: bool
        :return: ``True`` or ``False`` depending on whether the task has raised an
          exception.
        """
        return self.workgroup.exceptionRaised(self.id)