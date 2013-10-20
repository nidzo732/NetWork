from argparse import ArgumentParser


def getArgs():
    argumentParser = ArgumentParser(description="Server program that runs on worker computers in the NetWork framework")
    networkArgs = argumentParser.add_argument_group("Network settings")
    
    networkArgs.add_argument("-s", "--socket_type", 
                             help="Type of security applied to TCP communication with master, 'TCP' means no security",
                             default="TCP", choices=["TCP", "AES", "HMAC", "AES+HMAC"])
    
    networkArgs.add_argument("--incomming_hmac_key",
                             help="Key used to authenticate incomming messages with HMAC")
    
    networkArgs.add_argument("--master_hmac_key",
                             help="Key used to authenticate messages sent to master with HMAC")
    
    networkArgs.add_argument("--incomming_aes_key", 
                             help="Key used to decrypt incomming messages")
    
    networkArgs.add_argument("--master_aes_key", 
                             help="Key used to encrypt messages sent to master")

    networkArgs.add_argument("--master_ssl_cert",
                             help="Certificate file used to identify the master")

    networkArgs.add_argument("--local_ssl_cert",
                             help="Certificate used to verify this computer")

    networkArgs.add_argument("--local_ssl_key",
                             help="Private key used to decrypt incomming requests")

    networkArgs.add_argument("--local_key_password",
                             help="Password used to decrypt private key")
    args = argumentParser.parse_args()
    netArgs = {}
    
    if args.incomming_hmac_key:
        args.incomming_hmac_key = args.incomming_hmac_key.encode(encoding="ASCII")
        netArgs["ListenerHMAC"] = args.incomming_hmac_key
    
    if args.master_hmac_key:
        args.master_hmac_key = args.master_hmac_key.encode(encoding="ASCII")
    
    if args.incomming_aes_key:
        args.incomming_aes_key = args.incomming_aes_key.encode(encoding="ASCII")
        netArgs["ListenerAES"] = args.incomming_aes_key
    
    if args.master_aes_key:
        args.master_aes_key = args.master_aes_key.encode(encoding="ASCII")

    if args.master_ssl_cert:
        netArgs["PeerCertFile"] = args.master_ssl_cert

    if args.local_ssl_cert:
        netArgs["LocalCert"]=args.local_ssl_cert

    if args.local_ssl_key:
        netArgs["LocalKey"] = args.local_ssl_key

    if args.local_key_password:
        netArgs["LocalKeyPassword"] = args.local_key_password
    
    args.netArgs = netArgs
    return args