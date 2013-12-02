"""
The netPrint functionality enables tasks to print
their output on the masters screen.
"""
from .request import sendRequestWithResponse

CMD_NETPRINT = b"NPR"


def masterInit(workgroup):
    pass


def workerInit():
    pass


def netPrint(*args, **kwargs):
    """
    Print output to the masters screen.
    Parameters are the same as for the builtin print function
    """
    status = sendRequestWithResponse(CMD_NETPRINT, {"ARGS": args, "KWARGS": kwargs})
    if status == "OK":
        return
    else:
        raise status


def netPrintHandlerMaster(request, controls):
    try:
        print(*request["ARGS"], **request["KWARGS"])
        request.respond("OK")
    except TypeError as error:
        request.respond(error)


masterHandlers = {CMD_NETPRINT: netPrintHandlerMaster}
workerHandlers = {}