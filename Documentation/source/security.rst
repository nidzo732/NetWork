Securing network communication when using NetWork framework
***********************************************************
By default NetWork uses an unencrypted TCP communication, if that communication goes over insecure networks (like internet) anyone could see it and modify it, the worker computers happily accept any request which leaves them open to attacks.

Notes on key safety
###################
Please be advised that currently available security methods - HMAC and AES (a symetric cipher) rely on pre shared keys, it is your responsibility to deliver the keys where needed. 

In the future NetWork will support public key cryptography and eliminate the need to share secret keys over insecure chanels.

HMAC message authentication
###########################
If you just want to prevent unauthorized requests to worker and you don't care if the network communication can be seen, you can enable HMAC. Basicaly, when receiving messages from the master the worker checks if the master and worker have the same key, if the key is valid the worker accepts the request and handles it. For more detailed info about HMAC see `the wikipedia page <http://en.wikipedia.org/wiki/Hash-based_message_authentication_code>`_

Setting up HMAC on master
-------------------------
HMAC setup on master is done through the :py:class:`Workgroup` constructor, the constructor needs to be told to use HMAC, it needs to have a key to verify incomming connections and it needs a key for each worker, here's an example:

::

    #Create a workgroup that has two workes and use HMAC when communicating
    
    w=Workgroup([("192.168.1.105", b"Worker1HMACKey"), ("192.168.1.106", b"Worker2HMACKey")],
                 socket_type="HMAC", keys={"ListenerHMAC":b"MasterHMACKey"})

The first parameter would be a list of addresses when using an unprotected socket, but now it is a list of tuples that contain an address and a key used to send the messages, the :py:data:`socket_type` parameter tells the workgroup to use HMAC sockets, the :py:data:`keys` parameter is used to pass the listner key, that will be used to verify messages from the workers.

Setting up HMAC on worker
-------------------------
HMAC setup on worker is done through command line parameters, the incomming key and the master key are given to server.py. The master key is used when sending messages to the master and the incomming key is used to verify messages from the master.

.. code-block:: bash

    $ python3 server.py --socket_type HMAC --incomming_hmac_key Worker1HMACKey --master_hmac_key MasterHMACKey
    
This would be the setup for the first worker in the parameter list above, note that the worker key in the parameter list for :py:class:`Workgroup` must match ``--incomming_hmac_key`` in the command line parameters, and the master listener key must match ``--master_hmac_key``. For the second worker the setup would look like this 

.. code-block:: bash

    $ python3 server.py --socket_type HMAC --incomming_hmac_key Worker2HMACKey --master_hmac_key MasterHMACKey
    
As you can see, the worker key has changed but the master key remains the same.

AES message encryption
######################
If you don't want anyone to see what the workgroup is doing you can set it to encrypt all network communication with the AES encryption algorithm.

Setting up AES on master
------------------------
AES setup on master is done through the :py:class:`Workgroup` constructor, the constructor needs to be told to use AES, it needs to have a key to decrypt incomming connections and it needs a key for each worker, here's an example:

::

    #Create a workgroup that has two workes and use HMAC when communicating
    
    w=Workgroup([("192.168.1.105", b"Worker1AESKey"), ("192.168.1.106", b"Worker2AESKey")],
                 socket_type="AES", keys={"ListenerAES":b"MasterAESKey"})

The first parameter would be a list of addresses when using an unprotected socket, but now it is a list of tuples that contain an address and a key used to encrypt the messages, the :py:data:`socket_type` parameter tells the workgroup to use AES sockets, the :py:data:`keys` parameter is used to pass the listner key, that will be used to decrypt messages from the workers.

Setting up HMAC on worker
-------------------------
AES setup on worker is done through command line parameters, the incomming key and the master key are given to server.py. The master key is used when encrypting messages for the master and the incomming key is used to decrypt messages from the master.

.. code-block:: bash

    $ python3 server.py --socket_type AES --incomming_aes_key Worker1AESKey --master_hmac_key MasterAESKey
    
This would be the setup for the first worker in the parameter list above, note that the worker key in the parameter list for :py:class:`Workgroup` must match ``--incomming_aes_key`` in the command line parameters, and the master listener key must match ``--master_aes_key``. For the second worker the setup would look like this 

.. code-block:: bash

    $ python3 server.py --socket_type AES --incomming_aes_key Worker2AESKey --master_aes_key MasterAESKey
    
As you can see, the worker key has changed but the master key remains the same.

Using both AES and HMAC
#######################
Although AES encryption adds a hash to the message to check for tampering, you can enable bot AES and HMAC, you just need to give two sets of keys to the workgroup and to the worker, one for message verification and one for encryption/decryption.

Master setup
------------

::

    #Create a workgroup that has two workes and use HMAC when communicating
    
    w=Workgroup([("192.168.1.105", b"Worker1HMACKey", b"Worker1AESKey"), ("192.168.1.106", b"Worker2HMACKey", b"Worker2AESKey")],
                 socket_type="AES+HMAC", keys={"ListenerAES":b"MasterAESKey", "ListenerHMAC":b"MasterHMACKey"})

Each worker has a HMAC key and an AES key and master has HMAC and AES keys for incomming connections.

Worker setup
------------
Command line parameters for the first worker

.. code-block:: bash

    $ python3 server.py --socket_type AES+HMAC  --incomming_aes_key Worker1AESKey --master_aes_key MasterAESKey --incomming_hmac_key Worker1HMACKey --master_hmac_key MasterHMACKey