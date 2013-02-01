"""
This file will define a program that will run on the main computer
For now you may see some random code i used to test the package
"""
from NetWork.workgroup import WorkGroup
import time
w=WorkGroup(iprange=("192.168.1.2", "192.168.1.3"))
w.mainloop()
time.sleep(15)
w.halt()