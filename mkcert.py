import os
from argparse import ArgumentParser
import random

argParser = ArgumentParser(description="A helper script used to create SSL certificate for NetWork")
argParser.add_argument("PRIVATE_KEY_FILE", type=str,
                       help="Name of the file used to store the private key of the certificate")
argParser.add_argument("CERTIFICATE_FILE", type=str,
                       help="Name of the file used to store the SSL certificate")
argParser.add_argument("-k", "--keylength", type=int, default=4096,
                       help="Length of the RSA key used for the certificate")
argParser.add_argument("-e", "--encryptkey", action="store_true",
                       help="Encrypt the private key with a passphrase")
argParser.add_argument("-c", "--cipher", type=str, default="des3",
                       help="The cipher used to encrypt private key if --encryptkey is used")
argParser.add_argument("-d", "--duration", type=int, default=365,
                       help="Time duration before the certificate expires")

args = argParser.parse_args()
keyGenerationString = "openssl genrsa "
if args.encryptkey:
    keyGenerationString += "-" + args.cipher + " "

keyGenerationString += "-out " + args.PRIVATE_KEY_FILE + " " + str(args.keylength)
os.system(keyGenerationString)
random.seed()
csrfile = "tmp_csrfile_" + str(random.randint(500000, 500000000000))
certificateRequestString = "openssl req -new -key " + args.PRIVATE_KEY_FILE + " -out " + csrfile
os.system(certificateRequestString)
signatureString = "openssl x509 -req -days " + str(args.duration) + \
                  " -in " + csrfile + " -signkey " + args.PRIVATE_KEY_FILE + " -out " + args.CERTIFICATE_FILE
os.system(signatureString)
os.remove(csrfile)