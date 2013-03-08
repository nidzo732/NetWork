"""
This file will define a program that will run on the main computer
For now you may see some random code i used to test the package
"""
from NetWork import networking
s=networking.nwSocket()
s.bind()
s.listen()
while True:
    rcvd=s.accept()
    print(rcvd.commSocket.recv())