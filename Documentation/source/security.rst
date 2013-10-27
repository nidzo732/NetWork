Securing network communication when using NetWork framework
***********************************************************
By default NetWork uses an unencrypted TCP communication, if that communication goes over insecure networks (like
internet) anyone could see it and modify it, the worker computers happily accept any request which leaves them open
to attacks.

Warning
#######

**USE SSL IF YOU NEED ABSOULTE SECURITY**

The AES and HMAC security options are completely developed by me (author of NetWork). As far as I know
these methods are secure but I am not a crypto wizard and I have absolutely no experience in network security.
If SSL seems like an overkil to you use HMAC or AES, they are probably good enough in normal (non-military,
non-financial...) clusters but I cant guarantee that they are secure.

Homebrew cryptography is almost always insecure and a good cryptanalyst would probably find a flaw in my security
systems.

On the other hand SSL is a business proven security suite that stood the test of time for almost two decades.
The people who made SSL standard and OpenSSL (NetWork uses OpenSSL) are way better cryptographers than me.
If you need your cluster to be secure use the SSL option, it is a little harder to use but it is considered
unbreakable.


Notes on key safety
###################
Please be advised that  HMAC and AES  rely on pre shared keys, it is your responsibility to securely deliver the
keys where needed.

SSL does not have this problem, you still need to deliver the certificates but you don't need to wory about their
secrecy.

SSL network security
####################
SSL uses certificates to identify computers during communications, it also uses a public key encryption system
for secure communication. In NetWork the verification is done both ways, the workers verify the master and
the master verifies the workers, this prevents a third party from entering the cluster, either as a worker or
as a master.

Setup
-----

Creating certificates
=====================
The best way to create certificates for NetWork is to use the openssl command line tool. You can use self signed
certificates or you can have them signed by certificate authority.

For instructions on creating certificates see
`OpenSSL instructions <http://www.openssl.org/docs/HOWTO/certificates.txt>`_

Setting up master
=================
The master needs two parameters to use SSL. The first two are it's own SSL certificate and Key, these will enable
workers to verify the master and to secure the connection. The third parameter must point to a file or directory
that contains certificates of all workers. For instructions on how those files and directories must look see
`OpenSSL documentation <http://www.openssl.org/docs/ssl/SSL_CTX_load_verify_locations.html#NOTES>`_

These parameters are set in the constructor of the Workgroup through socketParams argument. Valid parameters are:

* ``PeerCertFile`` A file that contains SSL certificates that will be used to
  verify workers, you must provide PeerCertFile or PeerCertDir

* ``PeerCertDir`` A folder that contains SSL certificates that will be used to
  verify workers, you must provide either PeerCertFile or PeerCertDir or both

* ``LocalCert`` SSL certificate used to let workers verify this master
* ``LocalKey`` Private SSL key for this master)
* ``LocalKeyPassword`` Password used to decrypt local key if it's encrypted

Example:

::

    from NetWork import Workgroup

    #Create a workgroup that uses SSL secured network communication
    w=Workgroup([...workers...], socketType="SSL",
                socketParams={"PeerCertFile": "workerCerts.crt",
                              "LocalCert": "masterCert.crt",
                              "LocalKey": "masterKey.key"})
        #Do something with the workgroup

Setting up workers
==================
The worker also needs it's own SSL certificate and key and it needs the certificates are passed through command
line parameters. The parameters are:

* ``--master_ssl_cert MASTER_SSL_CERT`` Certificate file used to identify the master
* ``--local_ssl_cert LOCAL_SSL_CERT`` Certificate used to verify this worker
* ``--local_ssl_key LOCAL_SSL_KEY`` Private key used for SSL
* ``--local_key_password LOCAL_KEY_PASSWORD`` Password used to decrypt private key

An example:

.. code-block:: bash

    $ python3 server.py --master_ssl_cert masterCert.crt --local_ssl_cert worker1Cert.crt -local_ssl_key worker1Key.key

HMAC message authentication
###########################
If you just want to prevent unauthorized requests to worker and you don't care if the network communication can be
seen, you can enable HMAC. Basicaly, when receiving messages from the master the worker checks if the master and
worker have the same key, if the key is valid the worker accepts the request and handles it. For more detailed info
about HMAC see `the wikipedia page <http://en.wikipedia.org/wiki/Hash-based_message_authentication_code>`_

Setting up HMAC on master
-------------------------
HMAC setup on master is done through the :py:class:`Workgroup` constructor, the constructor needs to be told to use
HMAC, it needs to have a key to verify incomming connections and it needs a key for each worker, here's an example:

::

    #Create a workgroup that has two workes and use HMAC when communicating
    
    w=Workgroup([("192.168.1.105", b"Worker1HMACKey"), ("192.168.1.106", b"Worker2HMACKey")],
                 socket_type="HMAC", socketParams={"ListenerHMAC":b"MasterHMACKey"})

The first parameter would be a list of addresses when using an unprotected socket, but now it is a list of tuples
that contain an address and a key used to send the messages, the :py:data:`socket_type` parameter tells the
workgroup to use HMAC sockets, the :py:data:`socketParams` parameter is used to pass the listner key, that will be used
to verify messages from the workers.

Setting up HMAC on worker
-------------------------
HMAC setup on worker is done through command line parameters, the incomming key and the master key are given to
server.py. The master key is used when sending messages to the master and the incomming key is used to verify
messages from the master.

.. code-block:: bash

    $ python3 server.py --socket_type HMAC --incomming_hmac_key Worker1HMACKey --master_hmac_key MasterHMACKey
    
This would be the setup for the first worker in the parameter list above, note that the worker key in the parameter
list for :py:class:`Workgroup` must match ``--incomming_hmac_key`` in the command line parameters, and the master
listener key must match ``--master_hmac_key``. For the second worker the setup would look like this

.. code-block:: bash

    $ python3 server.py --socket_type HMAC --incomming_hmac_key Worker2HMACKey --master_hmac_key MasterHMACKey
    
As you can see, the worker key has changed but the master key remains the same.

AES message encryption
######################
If you don't want anyone to see what the workgroup is doing you can set it to encrypt all network communication
with the AES encryption algorithm.

Setting up AES on master
------------------------
AES setup on master is done through the :py:class:`Workgroup` constructor, the constructor needs to be told to use
AES, it needs to have a key to decrypt incomming connections and it needs a key for each worker, here's an example:

::

    #Create a workgroup that has two workes and use HMAC when communicating
    
    w=Workgroup([("192.168.1.105", b"Worker1AESKey"), ("192.168.1.106", b"Worker2AESKey")],
                 socket_type="AES", socketParams={"ListenerAES":b"MasterAESKey"})

The first parameter would be a list of addresses when using an unprotected socket, but now it is a list of tuples
that contain an address and a key used to encrypt the messages, the :py:data:`socket_type` parameter tells the
workgroup to use AES sockets, the :py:data:`socketParams` parameter is used to pass the listner key, that will be
used to decrypt messages from the workers.

Setting up HMAC on worker
-------------------------
AES setup on worker is done through command line parameters, the incomming key and the master key are given to
server.py. The master key is used when encrypting messages for the master and the incomming key is used to decrypt
messages from the master.

.. code-block:: bash

    $ python3 server.py --socket_type AES --incomming_aes_key Worker1AESKey --master_hmac_key MasterAESKey
    
This would be the setup for the first worker in the parameter list above, note that the worker key in the parameter
list for :py:class:`Workgroup` must match ``--incomming_aes_key`` in the command line parameters, and the master
listener key must match ``--master_aes_key``. For the second worker the setup would look like this

.. code-block:: bash

    $ python3 server.py --socket_type AES --incomming_aes_key Worker2AESKey --master_aes_key MasterAESKey
    
As you can see, the worker key has changed but the master key remains the same.

Using both AES and HMAC
#######################
Although AES encryption adds a hash to the message to check for tampering, you can enable bot AES and HMAC, you
just need to give two sets of keys to the workgroup and to the worker, one for message verification and one for
encryption/decryption.

Master setup
------------

::

    #Create a workgroup that has two workes and use HMAC when communicating
    
    w=Workgroup([("192.168.1.105", b"Worker1HMACKey", b"Worker1AESKey"), ("192.168.1.106", b"Worker2HMACKey", b"Worker2AESKey")],
                 socket_type="AES+HMAC", socketParams={"ListenerAES":b"MasterAESKey", "ListenerHMAC":b"MasterHMACKey"})

Each worker has a HMAC key and an AES key and master has HMAC and AES keys for incomming connections.

Worker setup
------------
Command line parameters for the first worker

.. code-block:: bash

    $ python3 server.py --socket_type AES+HMAC  --incomming_aes_key Worker1AESKey --master_aes_key MasterAESKey --incomming_hmac_key Worker1HMACKey --master_hmac_key MasterHMACKey