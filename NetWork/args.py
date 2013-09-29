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
    
    args=argumentParser.parse_args()
    netArgs={}
    
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
    
    args.netArgs=netArgs
    return args