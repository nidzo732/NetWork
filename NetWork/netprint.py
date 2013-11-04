from .networking import sendRequestWithResponse

CMD_NETPRINT = b"NPR"


def masterInit(workgroup):
    pass


def workerInit():
    pass


def netPrint(*args, **kwargs):
    status = sendRequestWithResponse(CMD_NETPRINT, {"ARGS": args, "KWARGS": kwargs})
    if status == "OK":
        return
    else:
        raise status


def netPrintHandlerMaster(request, controls, commqueue):
    try:
        print(*request["ARGS"], **request["KWARGS"])
        request.respond("OK")
    except TypeError as error:
        request.respond(error)


masterHandlers = {CMD_NETPRINT: netPrintHandlerMaster}
workerHandlers = {}

