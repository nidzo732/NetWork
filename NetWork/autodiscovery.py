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
    return discoveries[discoveryType].discoverWorkers(params)


def startDiscoveryServer(discoveryType, params={}):
    discoveries[discoveryType].startDiscoveryServer(params)