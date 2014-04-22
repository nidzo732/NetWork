"""
Autodiscovery lets the NetWork framework discovery worker computers for you.
Instead of typing the addresses manualy, you just run :py:meth:`discoverWorkers` and pass its output
to the Workgroup constructor.

Currently, only discovery via UDP multicast is supported.

Example

.. code-block:: python

    from NetWork import discoverWorkers, Workgroup
    workerList = discoverWorkers("UDP", {"TTL": 2, "TIMEOUT": 5})
    myWorkgorup = Workgroup(workerList)
        ...do something...

"""
from .networking import NWSocket
import socket
import struct
import threading
from multiprocessing import Queue

DEFAULT_MULTICAST_TTL = 1
DEFAULT_MULTICAST_GROUP = "224.5.6.7"
DEFAULT_MULTICAST_PORT = 32152
DEFAULT_DISCOVERY_TIMEOUT = 2
DEFAULT_REPEAT_COUNT = 3
DEFAULT_MULTICAST_MESSAGE = b"DISCOVERY"
DEFAULT_DISCOVERY_PORT = 32153

PARAM_CODE_TTL = "TTL"
PARAM_CODE_TIMEOUT = "TIMEOUT"
PARAM_CODE_REPEAT_COUNT = "REPEAT"


class UDPDiscovery:
    @staticmethod
    def discoverWorkers(params):
        ttl = DEFAULT_MULTICAST_TTL
        if PARAM_CODE_TTL in params:
            ttl = params[PARAM_CODE_TTL]
        timeout = DEFAULT_DISCOVERY_TIMEOUT
        if PARAM_CODE_TIMEOUT in params:
            timeout = params[PARAM_CODE_TIMEOUT]
        repeatCount = DEFAULT_REPEAT_COUNT
        if PARAM_CODE_REPEAT_COUNT in params:
            repeatCount = params[PARAM_CODE_REPEAT_COUNT]
        responseServer = NWSocket()
        responseServer.listen(DEFAULT_DISCOVERY_PORT)
        responseServer.setTimeout(timeout)
        responseQueue = Queue()
        responseThread = threading.Thread(target=UDPDiscovery.responseListenerThread,
                                          args=(responseServer, responseQueue))
        responseThread.start()
        emiterSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        emiterSocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack("b", ttl))
        for i in range(repeatCount):
            emiterSocket.sendto(DEFAULT_MULTICAST_MESSAGE, (DEFAULT_MULTICAST_GROUP, DEFAULT_MULTICAST_PORT))
        responseThread.join()
        addedIPs = set()
        while not responseQueue.empty():
            addedIPs.add(responseQueue.get())
        return addedIPs

    @staticmethod
    def responseListenerThread(listenerSocket, responseQueue):
        while True:
            try:
                newConnection = listenerSocket.accept()
                responseQueue.put(newConnection.address)
            except socket.timeout:
                return

    @staticmethod
    def responseSenderThread():
        listenerSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listenerSocket.bind(("0.0.0.0", DEFAULT_MULTICAST_PORT))
        socketSettings = struct.pack("4sL", socket.inet_aton(DEFAULT_MULTICAST_GROUP), socket.INADDR_ANY)
        listenerSocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socketSettings)
        while True:
            data, address = listenerSocket.recvfrom(1024)
            responder = NWSocket()
            responder.connect(address[0], DEFAULT_DISCOVERY_PORT)
            responder.send(b"DISCOVERY_RESPONSE")

    @staticmethod
    def startDiscoveryServer(params):
        responderThread = threading.Thread(target=UDPDiscovery.responseSenderThread)
        responderThread.daemon = True
        responderThread.start()


discoveries = {"UDP": UDPDiscovery}


def discoverWorkers(discoveryType, params={}):
    """
    Discover worker computers on the network. Returns a list of worker addresses which can then be passed
    to :py:class:`Workgroup` constructor.

    :type discoveryType: str
    :param discoveryType: Method to use for discovery. Currently, only UDP multicast is available.
    :type params: dict
    :param params: Additional parameters for the discovery method

        * UDP:

          * :py:data:`"TTL"` time to live, how many routers will the discovery packet go through
            :py:data:`1` usually means local network
          * :py:data:`"TIMEOUT"` how long (in seconds) to wait for a response from workers, default is :py:data:`2`
          * :py:data:`"REPEAT"` how many times to send a discovery packet, increase if the packet loss is high


    :return: a list of discovered worker addresses
    """
    return discoveries[discoveryType].discoverWorkers(params)


def startDiscoveryServer(discoveryType, params={}):
    discoveries[discoveryType].startDiscoveryServer(params)