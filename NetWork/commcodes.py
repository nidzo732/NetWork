"""
3 letter codes prepended to each message to determine
which handler should be used for that message
"""
CMD_HALT = b"HLT"
CMD_SUBMIT_TASK = b"TSK"
CMD_TERMINATE_TASK = b"TRM"
CMD_GET_RESULT = b"RSL"
CMD_TASK_RUNNING = b"TRN"
CMD_GET_EXCEPTION = b"EXC"
CMD_CHECK_EXCEPTION = b"EXR"
CMD_WORKER_DIED = b"DWR"