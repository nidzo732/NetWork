NetWork specific tools
**********************

The networked architecture sometimes requires usage of specific tools that don't represent those from
multiprocessing module.

Using custom objects
####################
To use objects that do not belong to python bultins you need to wrap them with :doc:`NetObject <NetObject>`

Printing
########
If you want the output from your tasks to show up on the master screen you need to use :doc:`netPrint <NetPrint>`
instead of regular print call.