"""
This module implements a socket classes used to safely handle
network messaging, message length and security.
"""
import socket
import hmac
import hashlib
from multiprocessing import Lock

try:
    from Crypto.Cipher import AES
    from Crypto import Random

    cryptoAvailable = True
except ImportError:
    cryptoAvailable = False

try:
    from ssl import SSLContext, PROTOCOL_TLSv1, CERT_REQUIRED, SSLError, SSLSocket

    SSLAvailable = True
except ImportError:
    SSLAvailable = False

COMCODE_CHECKALIVE = b"ALV"
COMCODE_ISALIVE = b"IMALIVE"
ISALIVE_TIMEOUT = 10
DEFAULT_TCP_PORT = 32151
BUFFER_READ_LENGTH = 4096
MESSAGE_LENGTH_DELIMITER = b"MLEN"
MAX_MESSAGELENGTH_LENGTH = 10
DEFAULT_LISTENING_ADDRESS = bytes(socket.INADDR_ANY)
LISTEN_QUEUE_LENGTH = 5
DEFAULT_SOCKET_TIMEOUT = 5.0
AES_KEY_LENGTH = 16
AES_IV_LENGTH = 16
MAX_MESSAGELENGTH_LENGTH += len(MESSAGE_LENGTH_DELIMITER)
workgroup = None
masterAddress = None


class InvalidMessageFormatError(OSError): pass


class MessageNotCompleteError(OSError): pass


class UnauthenticatedMessage(OSError): pass


class LengthIndicatorTooLong(OSError): pass


class KeyNotSet(OSError): pass


class SSLProblem(OSError):
    pass


masterAddress = None


class NWSocketTCP:
    #Currently the default socket class that implements a
    #classic TCP communication
    def __init__(self, socketToUse=None, address=None):
        if socketToUse:
            self.internalSocket = socketToUse
        else:
            self.internalSocket = socket.socket(socket.AF_INET,
                                                socket.SOCK_STREAM)

        self.internalSocket.setsockopt(socket.SOL_SOCKET,
                                       socket.SO_REUSEADDR, 1)
        self.internalSocket.settimeout(DEFAULT_SOCKET_TIMEOUT)
        self.address = address

    def listen(self, port=DEFAULT_TCP_PORT):
        #listen for incomming connections
        self.internalSocket.settimeout(None)
        self.internalSocket.bind((DEFAULT_LISTENING_ADDRESS, port))
        self.internalSocket.listen(LISTEN_QUEUE_LENGTH)

    def setTimeout(self, timeout):
        self.internalSocket.settimeout(timeout)

    def recv(self):
        #safely receive all sent data
        receivedData = b""
        while receivedData.find(MESSAGE_LENGTH_DELIMITER) == -1:
            if len(receivedData) > MAX_MESSAGELENGTH_LENGTH:
                raise LengthIndicatorTooLong
            if not NWSocketTCP.checkMessageFormat(receivedData):
                raise InvalidMessageFormatError("Received string not formatted properly")
            newData = self.internalSocket.recv(BUFFER_READ_LENGTH)
            if len(newData) == 0:
                raise MessageNotCompleteError(
                    b"Socket got closed before receiving the entire message, got only: " + receivedData)
            receivedData += newData
        if not NWSocketTCP.checkMessageFormat(receivedData):
            raise InvalidMessageFormatError("Received string not formatted properly")
        sizelen = receivedData.find(MESSAGE_LENGTH_DELIMITER)
        messageLength = int(receivedData[0:sizelen])
        receivedData = receivedData[sizelen + len(MESSAGE_LENGTH_DELIMITER):]
        while len(receivedData) < messageLength:
            newData = self.internalSocket.recv(BUFFER_READ_LENGTH)
            if len(newData) == 0:
                raise MessageNotCompleteError("socket got closed before receiving the entire message")
            receivedData += newData
        return receivedData

    def send(self, data):
        #send given data
        dataLength = str(len(data)).encode(encoding="ASCII")
        message = dataLength + MESSAGE_LENGTH_DELIMITER + data
        self.internalSocket.sendall(message)

    def connect(self, address, port=DEFAULT_TCP_PORT):
        #connect to the address
        self.address = address
        self.internalSocket.connect((address, port))

    def accept(self, timeout=0):
        #accept a connection request and return a communication socket
        requestData = self.internalSocket.accept()
        return NWSocket(requestData[0], requestData[1][0])

    def close(self):
        #close the socket
        self.internalSocket.close()

    @staticmethod
    def checkAvailability(address):
        #check if there's a worker on the address     
        testSocket = NWSocket()
        try:
            testSocket.connect(address)
            testSocket.send(COMCODE_CHECKALIVE)
            response = testSocket.recv()
        except OSError:
            return False, None

        return response == COMCODE_ISALIVE, testSocket.address

    @staticmethod
    def checkMessageFormat(message):
        #check if a message fits the format
        if not message:
            return True
        elif not (message[0] in range(48, 59)):
            return False
        else:
            for i in enumerate(message):
                if not i[1] in range(48, 59):
                    p = i[0]
                    break
            else:
                return True
            message = message[p:]
            if len(message) == len(MESSAGE_LENGTH_DELIMITER):
                return message == MESSAGE_LENGTH_DELIMITER
            elif len(message) < len(MESSAGE_LENGTH_DELIMITER):
                return message == MESSAGE_LENGTH_DELIMITER[:len(message)]
            else:
                return message[:len(MESSAGE_LENGTH_DELIMITER)] == MESSAGE_LENGTH_DELIMITER

    @staticmethod
    def setUp(keys):
        pass


class NWSocketHMAC(NWSocketTCP):
    #A socket class that implements HMAC message verification
    listenerHMAC = None

    def __init__(self, socketToUse=None, parameters=None):
        if socketToUse:
            NWSocketTCP.__init__(self, socketToUse, parameters[0])
            self.HMACKey = parameters[1]
        else:
            NWSocketTCP.__init__(self)

    def listen(self):
        if not self.listenerHMAC:
            raise KeyNotSet("The HMAC key for listener sockets was not set")
        NWSocketTCP.listen(self)

    def connect(self, parameters):
        NWSocketTCP.connect(self, parameters[0])
        self.address = parameters[0]
        self.HMACKey = parameters[1]

    def recv(self):
        receivedData = NWSocketTCP.recv(self)
        hashLength = hashlib.sha256().digest_size
        message = receivedData[:-hashLength]
        receivedHash = receivedData[-hashLength:]
        messageHash = hmac.new(key=self.HMACKey, msg=message, digestmod=hashlib.sha256)

        try:
            messageValid = hmac.compare_digest(messageHash.digest(), receivedHash)
        except AttributeError:
            #Python version<3.3 doesn't have compare_digest
            #so I had to rely on a less secure comparison with ==
            messageValid = (messageHash.digest() == receivedHash)

        if messageValid:
            return message
        else:
            raise UnauthenticatedMessage("Bad HMAC")

    def send(self, data):
        messageHash = hmac.new(key=self.HMACKey, msg=data, digestmod=hashlib.sha256)
        hash = messageHash.digest()
        message = data + hash
        NWSocketTCP.send(self, message)

    def accept(self):
        requestData = self.internalSocket.accept()
        return NWSocketHMAC(requestData[0], (requestData[1][0], self.listenerHMAC))

    @staticmethod
    def setUp(keys):
        NWSocketHMAC.listenerHMAC = keys["ListenerHMAC"]


sockets = {"TCP": NWSocketTCP, "HMAC": NWSocketHMAC}
NWSocket = NWSocketTCP   # set default socket used in the framework

if cryptoAvailable:
    def AESEncrypt(data, key):
        keygen = hashlib.sha256()
        hashgen = hashlib.sha256()
        keygen.update(key)
        hashgen.update(data)
        aesKey = keygen.digest()
        data += hashgen.digest()
        Random.atfork()
        initializationVector = Random.new().read(AES_IV_LENGTH)
        cipher = AES.new(aesKey, AES.MODE_CFB, initializationVector)
        return initializationVector + cipher.encrypt(data)

    def AESDecrypt(data, key):
        keygen = hashlib.sha256()
        hashgen = hashlib.sha256()
        keygen.update(key)
        aesKey = keygen.digest()
        initializationVector = b"1234567890123456"
        cipher = AES.new(aesKey, AES.MODE_CFB, initializationVector)
        decryptedData = cipher.decrypt(data)[AES_IV_LENGTH:]
        hash = decryptedData[-hashgen.digest_size:]
        data = decryptedData[:-hashgen.digest_size]
        hashgen.update(data)
        try:
            messageValid = hmac.compare_digest(hashgen.digest(), hash)
        except AttributeError:
        #Python version<3.3 doesn't have compare_digest
            #so I had to rely on a less secure comparison with ==
            messageValid = (hashgen.digest() == hash)
        if messageValid:
            return data
        else:
            raise UnauthenticatedMessage("Bad decryption")

    class NWSocketAES(NWSocketTCP):
        #A socket class that implements AES message encryption
        listenerAES = None

        def __init__(self, socketToUse=None, parameters=None):
            if socketToUse:
                NWSocketTCP.__init__(self, socketToUse, parameters[0])
                self.AESKey = parameters[1]
            else:
                NWSocketTCP.__init__(self)

        def listen(self):
            if not self.listenerAES:
                raise KeyNotSet("The AES key for listener sockets was not set")
            NWSocketTCP.listen(self)

        def connect(self, parameters):
            NWSocketTCP.connect(self, parameters[0])
            self.address = parameters[0]
            self.AESKey = parameters[1]

        def accept(self):
            requestData = self.internalSocket.accept()
            return NWSocketAES(requestData[0], (requestData[1][0], self.listenerAES))

        def recv(self):
            receivedData = NWSocketTCP.recv(self)
            decryptedData = AESDecrypt(receivedData, self.AESKey)
            return decryptedData

        def send(self, data):
            encryptedData = AESEncrypt(data, self.AESKey)
            NWSocketTCP.send(self, encryptedData)

        @staticmethod
        def setUp(keys):
            NWSocketAES.listenerAES = keys["ListenerAES"]

    class NWSocketHMACandAES(NWSocketHMAC):
        #A socket class that implemets HMAC message verification and
        #AES message encryption
        listenerAES = None
        listenerHMAC = None

        def __init__(self, socketToUse=None, address=None, AESKey=None,
                     HMACKey=None):
            if socketToUse:
                NWSocketHMAC.__init__(self, socketToUse, (address, HMACKey))
                self.AESKey = AESKey
            else:
                NWSocketHMAC.__init__(self)

        def accept(self):
            requestData = self.internalSocket.accept()
            return NWSocketHMACandAES(requestData[0], requestData[1][0],
                                      self.listenerAES, self.listenerHMAC)

        def listen(self):
            if not self.listenerAES:
                raise KeyNotSet("The AES key for listener sockets was not set")
            NWSocketHMAC.listen(self)

        def connect(self, parameters):
            NWSocketHMAC.connect(self, (parameters[0], parameters[1]))
            self.address = parameters[0]
            self.AESKey = parameters[2]

        def recv(self):
            receivedData = NWSocketHMAC.recv(self)
            decryptedData = AESDecrypt(receivedData, self.AESKey)
            return decryptedData

        def send(self, data):
            encryptedData = AESEncrypt(data, self.AESKey)
            NWSocketHMAC.send(self, encryptedData)

        @staticmethod
        def setUp(keys):
            NWSocketHMACandAES.listenerAES = keys["ListenerAES"]
            NWSocketHMACandAES.listenerHMAC = keys["ListenerHMAC"]


else:
    class NWSocketAES:
        @staticmethod
        def setUp(keys):
            raise NotImplementedError("AES could not be used because PyCrypto module is not available")

    class NWSocketHMACandAES(NWSocketAES):
        pass

if SSLAvailable:
    class NWSocketSSL(NWSocketTCP):
        localCertFile = None
        localKeyFile = None
        localKeyPassword = None
        peerCertFile = None
        peerCertDir = None
        context = None
        sockets = []
        socketLock = Lock()

        def __init__(self, socketToUse=None, address=None):
            if socketToUse:
                self.internalSocket = socketToUse
            else:
                NWSocketTCP.__init__(self)
            self.address = address

        def connect(self, address):
            try:
                self.internalSocket = self.context.wrap_socket(self.internalSocket)
                NWSocketTCP.connect(self, address)
            except SSLError as error:
                raise SSLProblem("SSL connection failed ", error)

        def accept(self):
            try:
                request = self.internalSocket.accept()
                sock = request[0]
                address = request[1][0]
                sock = self.context.wrap_socket(sock, server_side=True)
                return NWSocketSSL(sock, address)
            except SSLError as error:
                raise SSLProblem("Bad request received ", error)

        def __getstate__(self):
            self.socketLock.acquire()
            self.sockets.append(self.internalSocket)
            sockId = len(self.sockets) - 1
            self.socketLock.release()
            return {"address": self.address, "sockId": sockId}

        def __setstate__(self, state):
            self.address = state["address"]
            self.internalSocket = self.sockets[state["sockId"]]

        @staticmethod
        def setUp(params):
            NWSocketSSL.localCertFile = params["LocalCert"]
            NWSocketSSL.localKeyFile = params["LocalKey"]
            if (not "PeerCertFile" in params) and (not "PeerCertDir" in params):
                raise KeyError("PeerCertFile or PeerCertDir")
            if "PeerCertFile" in params:
                NWSocketSSL.peerCertFile = params["PeerCertFile"]
            if "PeerCertDir" in params:
                NWSocketSSL.peerCertDir = params["PeerCertDir"]
            if "LocalKeyPassword" in params:
                NWSocketSSL.localKeyPassword = params["LocalKeyPassword"]

            NWSocketSSL.context = SSLContext(PROTOCOL_TLSv1)
            NWSocketSSL.context.load_cert_chain(certfile=NWSocketSSL.localCertFile, keyfile=NWSocketSSL.localKeyFile,
                                                password=NWSocketSSL.localKeyPassword)
            NWSocketSSL.context.load_verify_locations(cafile=NWSocketSSL.peerCertFile,
                                                      capath=NWSocketSSL.peerCertDir)
            NWSocketSSL.context.verify_mode = CERT_REQUIRED

else:
    class NWSocketSSL:
        @staticmethod
        def setUp(keys):
            raise NotImplementedError("SSL could not be used because SSL module is not available")

sockets.update({"AES": NWSocketAES, "AES+HMAC": NWSocketHMACandAES,
                "SSL": NWSocketSSL})


def setUp(socketType, params):
    if socketType:
        try:
            sockets[socketType].setUp(params)
        except KeyError as error:
            raise KeyNotSet("Not all parameters were set for the desired security type: "
                            + str(socketType) + " could not find " + str(error))
        global NWSocket
        NWSocket = sockets[socketType]