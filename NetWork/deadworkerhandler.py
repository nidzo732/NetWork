class AllWorkersDeadError(Exception):pass
class DeadWorkerError(Exception):
    def __init__(self, message, deadWorker):
        self.deadWorker=deadWorker
        Exception.__init__(self, message)

def salvageDeadWorker(workgroup, id=None, worker=None):
    if workgroup.handleDeadWorkers:
        if id:
            if workgroup.workerList[worker].alive:
                workgroup.controlls[CNT_LIVE_WORKERS]-=1
                if not workgroup.controlls[CNT_LIVE_WORKERS]:
                    raise AllWorkersDeadError("Lost connection to all workers")
                workgroup.workerList[worker].alive=False
            failedTask=workgroup.workerList[worker].myTasks[id]
            newHandler=workgroup.submit(failedTask.target, failedTask.args, 
                                   failedTask.kwargs)
            return newHandler
        else:
            workgroup.controlls[CNT_LIVE_WORKERS]-=1
            if not workgroup.controlls[CNT_LIVE_WORKERS]:
                raise AllWorkersDeadError("Lost connection to all workers")
            workgroup.workerList[worker].alive=False
    else:
        raise DeadWorkerError("Lost connection to worker #"+str(worker)),
                              workgroup.workerList[worker])