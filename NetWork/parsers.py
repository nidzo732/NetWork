"""

This file defines various parsers used throughout the program.
Most are static methods grouped by classes according to their purpose.

Created on Jan 11, 2013
"""

#Exceptions raised by functions in this module
class InvalidIPRangeError(Exception):
    def __init__(self, iprange):
        Exception.__init__(self, """Range """+str(iprange)+"""
is invalid. Required format is an iterable with two elements
first one is the first address, and the second one is the last
Both have to be VALID IP ADDRESSES""")

class IPParsers:
    """
    Parsers for ip addresses
    """
    @staticmethod
    def parseIPRange(iprange):
        """
        Generate a range list of ip addresses
        iprange-> a (first, last) tuple defining the first
        and last IP in the range
        returns a tuple of ip addresses
        """
        if len(iprange)!=2:     #Is the range formatted right
            raise InvalidIPRangeError(iprange)
        begin=iprange[0]
        end=iprange[1]
        if not (IPParsers.isValidIP(begin) and IPParsers.isValidIP(end)):
            raise InvalidIPRangeError(iprange)      #Are both addresses valid
        begin=IPParsers.IPToList(begin)
        end=IPParsers.IPToList(end)
        parsedrange=()
        while begin!=end:
            parsedrange+=(IPParsers.listToIP(begin),)
            IPParsers.incrementIP(begin, 3)
        parsedrange+=(IPParsers.listToIP(end),)
        return parsedrange
            
          
    
    @staticmethod
    def isValidIP(ip):
        """
        Checks is the given ip valid
        """
        try:
            parts=ip.split(".")
            if len(parts)!=4:
                return False
            for i in parts:
                if int(i)>255 or int(i)<0:
                    return False
            return True
        except:
            return False
    
    @staticmethod
    def IPToList(ip):
        """
        Converts the given IP string to a four element list
        """
        parsedip=[]
        for i in ip.split("."):
            parsedip.append(int(i))
        return parsedip
    
    @staticmethod
    def listToIP(lst):
        """
        Converts a given four element list to an IP string
        """
        ipstring=""
        for i in lst:
            ipstring+=str(i)+"."
        return ipstring[:-1]
    
    @staticmethod
    def incrementIP(ip, position):
        """
        Increment the given position of the ip
        this may sound weird, here are some IPs given in ascending order:
        192.168.1.253, 192.168.1.254, 192.168.2.1, 192.168.2.2
        """
        if ip[position]==254:   #Should this be 255
            ip[position]=1
            IPParsers.incrementIP(ip, position-1)
        else:
            ip[position]+=1

#Less typing for other modules
parseIPRange=IPParsers.parseIPRange
