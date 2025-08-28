#!/usr/bin/python3

#
# Tests of the packet assembler/disassembler routines.
#
# only tests the simple packers for now. next is to test the
# classes: Hpacker/Hunpacker,
# Qpacker/Unpacker, then Mpacker/Munpacker
#
# Start doing unpleasant tests with broken data, truncations, that
# sort of thing.

import sys ; sys.path.insert(0, '..')
import DNS
import socket
import unittest

TestCompleted = "TestCompleted" # exc.

class Int16Packing(unittest.TestCase):
    knownValues = ( ( 10, b'\x00\n'),
                   ( 500, b'\x01\xf4' ),
                   ( 5340, b'\x14\xdc' ),
                   ( 51298, b'\xc8b'),
                   ( 65535, b'\xff\xff'),
                   )

    def test16bitPacking(self):
        """ pack16bit should give known output for known input """
        for i,s in self.knownValues:
            result = DNS.Lib.pack16bit(i)
            self.assertEqual(s,result)

    def test16bitUnpacking(self):
        """ unpack16bit should give known output for known input """
        for i,s in self.knownValues:
            result = DNS.Lib.unpack16bit(s)
            self.assertEqual(i,result)

class Int32Packing(unittest.TestCase):
    knownValues = ( ( 10, b'\x00\x00\x00\n'),
                   ( 500, b'\x00\x00\x01\xf4' ),
                   ( 5340, b'\x00\x00\x14\xdc' ),
                   ( 51298, b'\x00\x00\xc8b'),
                   ( 65535, b'\x00\x00\xff\xff'),
                   ( 33265535, b'\x01\xfb\x97\x7f' ),
                   ( 147483647, b'\x08\xcak\xff' ),
                   ( 2147483647, b'\x7f\xff\xff\xff' ),
                   )
    def test32bitPacking(self):
        """ pack32bit should give known output for known input """
        for i,s in self.knownValues:
            result = DNS.Lib.pack32bit(i)
            self.assertEqual(s,result)

    def test32bitUnpacking(self):
        """ unpack32bit should give known output for known input """
        for i,s in self.knownValues:
            result = DNS.Lib.unpack32bit(s)
            self.assertEqual(i,result)


class IPaddrPacking(unittest.TestCase):
    knownValues = (
                    ('127.0.0.1', 2130706433 ),
                    ('10.99.23.13', 174266125 ),
                    ('192.35.59.45', 3223534381), # Not signed anymore - it's all long now.
                    ('255.255.255.255', 4294967295) # No longer -1
                    )

    def testIPaddrPacking(self):
        """ addr2bin should give known output for known input """
        for i,s in self.knownValues:
            result = DNS.Lib.addr2bin(i)
            self.assertEqual(s,result)

    def testIPaddrUnpacking(self):
        """ bin2addr should give known output for known input """
        for i,s in self.knownValues:
            result = DNS.Lib.bin2addr(s)
            self.assertEqual(i,result)

class PackerClassPacking(unittest.TestCase):
    knownPackValues = [
        ( ['www.ekit.com'], b'\x03www\x04ekit\x03com\x00' ),
        ( ['ns1.ekorp.com', 'ns2.ekorp.com', 'ns3.ekorp.com'],
               b'\x03ns1\x05ekorp\x03com\x00\x03ns2\xc0\x04\x03ns3\xc0\x04'),
        ( ['a.root-servers.net.', 'b.root-servers.net.',
           'c.root-servers.net.', 'd.root-servers.net.',
           'e.root-servers.net.', 'f.root-servers.net.'],
               b'\x01a\x0croot-servers\x03net\x00\x01b\xc0\x02\x01c\xc0'+
               b'\x02\x01d\xc0\x02\x01e\xc0\x02\x01f\xc0\x02' ),
        ]
    knownUnpackValues = [
        ( ['www.ekit.com'], b'\x03www\x04ekit\x03com\x00' ),
        ( ['ns1.ekorp.com', 'ns2.ekorp.com', 'ns3.ekorp.com'],
               b'\x03ns1\x05ekorp\x03com\x00\x03ns2\xc0\x04\x03ns3\xc0\x04'),
        ( ['a.root-servers.net', 'b.root-servers.net',
           'c.root-servers.net', 'd.root-servers.net',
           'e.root-servers.net', 'f.root-servers.net'],
               b'\x01a\x0croot-servers\x03net\x00\x01b\xc0\x02\x01c\xc0'+
               b'\x02\x01d\xc0\x02\x01e\xc0\x02\x01f\xc0\x02' ),
        ]

    def testPackNames(self):
        from DNS.Lib import Packer
        for namelist,result in self.knownPackValues:
            p = Packer()
            for n in namelist:
                p.addname(n)
            self.assertEqual(p.getbuf(),result)

    def testUnpackNames(self):
        from DNS.Lib import Unpacker
        for namelist,result in self.knownUnpackValues:
            u = Unpacker(result)
            names = []
            for i in range(len(namelist)):
                n = u.getname()
                names.append(n)
            self.assertEqual(names, namelist)

"""    def testUnpackerLimitCheck(self):
       # FIXME: Don't understand what this test should do. If my guess is right,
       # then the code is working ~OK.
        from DNS.Lib import Unpacker
        u=Unpacker(b'\x03ns1\x05ekorp\x03com\x00\x03ns2\xc0\x04\x03ns3\xc0\x04')
        u.getname() ; u.getname() ; u.getname()
        # 4th call should fail
        self.assertRaises(IndexError, u.getname)"""

class testUnpackingMangled(unittest.TestCase):
    "addA(self, name, klass, ttl, address)"
    packerCorrect = b'\x05www02\x04ekit\x03com\x00\x00\x01\x00\x01\x00\x01Q\x80\x00\x04\xc0\xa8\n\x02'
    def testWithoutRR(self):
        u = DNS.Lib.RRunpacker(self.packerCorrect)
        u.getAdata()
    def testWithTwoRRs(self):
        u = DNS.Lib.RRunpacker(self.packerCorrect)
        u.getRRheader()
        self.assertRaises(DNS.Lib.UnpackError, u.getRRheader)
    def testWithNoGetData(self):
        u = DNS.Lib.RRunpacker(self.packerCorrect)
        u.getRRheader()
        self.assertRaises(DNS.Lib.UnpackError, u.endRR)

class PackerTestCase(unittest.TestCase):
    " base class for tests of Packing code. Laziness on my part, I know. "
    def setUp(self):
        self.RRpacker = DNS.Lib.RRpacker
        self.RRunpacker = DNS.Lib.RRunpacker
        
    def testPacker(self):
        p = self.RRpacker()
        check = self.doPack(p)
        if (p is not None) and (check is not TestCompleted):
            return self.checkPackResult(p)

    def checkPackResult(self, buf):
        if not hasattr(self, 'packerExpectedResult'):
            if self.__class__.__name__ != 'PackerTestCase':
                print("P***", self, repr(buf.getbuf())) #cheat testcase
        else:
            return self.assertEqual(buf.getbuf(),
                                self.packerExpectedResult)

    def checkUnpackResult(self, rrbits, specbits):
        if not hasattr(self, 'unpackerExpectedResult'):
            if self.__class__.__name__ != 'PackerTestCase':
                print("U***", self, repr((rrbits,specbits))) #cheat testcase
        else:
            return self.assertEqual((rrbits, specbits),
                                self.unpackerExpectedResult)

    def testUnpacker(self):
        if self.doUnpack is not None:
            if hasattr(self.__class__, 'doUnpack') \
                    and hasattr(self, 'packerExpectedResult'):
                u = self.RRunpacker(self.packerExpectedResult)
                rrbits = u.getRRheader()[:4]
                specbits = self.doUnpack(u)
                try:
                    u.endRR()
                except DNS.Lib.UnpackError:
                    self.assertEqual(0, 'Not at end of RR!')
                return self.checkUnpackResult(rrbits, specbits)
            else:
                me = self.__class__.__name__
                if me != 'PackerTestCase':
                    self.assertEquals(self.__class__.__name__,
                                                'Unpack NotImplemented')

    def doPack(self, p):
        " stub. don't test the base class "
        return None

    def doUnpack(self, p):
        " stub. don't test the base class "
        return None


class testPackingOfCNAME(PackerTestCase):
    "addCNAME(self, name, klass, ttl, cname)"
    def doPack(self,p):
        p.addCNAME('www.sub.domain', DNS.Class.IN, 3600, 'realhost.sub.domain')
    def doUnpack(self, u):
        return u.getCNAMEdata()

    unpackerExpectedResult = (('www.sub.domain', DNS.Type.CNAME, DNS.Class.IN, 3600), 'realhost.sub.domain')
    packerExpectedResult = \
                b'\x03www\x03sub\x06domain\x00\x00\x05\x00\x01\x00'+ \
                b'\x00\x0e\x10\x00\x0b\x08realhost\xc0\x04'

class testPackingOfCNAME2(PackerTestCase):
    "addCNAME(self, name, klass, ttl, cname)"
    def doPack(self,p):
        p.addCNAME('www.cust.com', DNS.Class.IN, 200, 'www023.big.isp.com')
    def doUnpack(self, u):
        return u.getCNAMEdata()
    unpackerExpectedResult = (('www.cust.com', DNS.Type.CNAME, DNS.Class.IN, 200), 'www023.big.isp.com')
    packerExpectedResult = \
                b'\x03www\x04cust\x03com\x00\x00\x05\x00\x01\x00'+ \
                b'\x00\x00\xc8\x00\x11\x06www023\x03big\x03isp\xc0\t'

class testPackingOfCNAME3(PackerTestCase):
    "addCNAME(self, name, klass, ttl, cname)"
    def doPack(self,p):
        p.addCNAME('www.fred.com', DNS.Class.IN, 86400, 'webhost.loa.com')
    def doUnpack(self, u):
        return u.getCNAMEdata()
    unpackerExpectedResult = (('www.fred.com', DNS.Type.CNAME, DNS.Class.IN, 86400), 'webhost.loa.com')
    packerExpectedResult = \
                b'\x03www\x04fred\x03com\x00\x00\x05\x00\x01\x00\x01Q'+ \
                b'\x80\x00\x0e\x07webhost\x03loa\xc0\t'

class testPackingOfHINFO(PackerTestCase):
    "addHINFO(self, name, klass, ttl, cpu, os)"
    def doPack(self,p):
        p.addHINFO('www.sub.domain.com', DNS.Class.IN, 3600, 'i686', 'linux')
    def doUnpack(self, u):
        return u.getHINFOdata()
    unpackerExpectedResult = (('www.sub.domain.com', 13, 1, 3600), ('i686', 'linux'))
    packerExpectedResult = \
                b'\x03www\x03sub\x06domain\x03com\x00\x00\r\x00\x01'+ \
                b'\x00\x00\x0e\x10\x00\x0b\x04i686\x05linux'

class testPackingOfHINFO2(PackerTestCase):
    "addHINFO(self, name, klass, ttl, cpu, os)"
    def doPack(self,p):
        p.addHINFO('core1.lax.foo.com', DNS.Class.IN, 3600, 'cisco', 'ios')
    def doUnpack(self, u):
        return u.getHINFOdata()
    unpackerExpectedResult = (('core1.lax.foo.com', 13, 1, 3600), ('cisco', 'ios'))
    packerExpectedResult = \
                b'\x05core1\x03lax\x03foo\x03com\x00\x00\r\x00\x01'+ \
                b'\x00\x00\x0e\x10\x00\n\x05cisco\x03ios'

class testPackingOfMX(PackerTestCase):
    "addMX(self, name, klass, ttl, preference, exchange)"
    def doPack(self, p):
        p.addMX('sub.domain.com', DNS.Class.IN, 86400, 10, 'mailhost1.isp.com')
    def doUnpack(self, u):
        return u.getMXdata()
    packerExpectedResult = \
                b'\x03sub\x06domain\x03com\x00\x00\x0f\x00\x01'+ \
                b'\x00\x01Q\x80\x00\x12\x00\n\tmailhost1\x03isp\xc0\x0b'
    unpackerExpectedResult = (('sub.domain.com', 15, 1, 86400), (10, 'mailhost1.isp.com'))

class testPackingOfMX2(PackerTestCase):
    "addMX(self, name, klass, ttl, preference, exchange)"
    def doPack(self, p):
        p.addMX('ekit-inc.com.', DNS.Class.IN, 86400, 10, 'mx1.ekorp.com')
        p.addMX('ekit-inc.com.', DNS.Class.IN, 86400, 20, 'mx2.ekorp.com')
        p.addMX('ekit-inc.com.', DNS.Class.IN, 86400, 30, 'mx3.ekorp.com')
    def doUnpack(self, u):
        res = [u.getMXdata(),]
        dummy = u.getRRheader()[:4]
        res += u.getMXdata()
        dummy = u.getRRheader()[:4]
        res += u.getMXdata()
        return res
    unpackerExpectedResult = (('ekit-inc.com', 15, 1, 86400), [(10, 'mx1.ekorp.com'), 20, 'mx2.ekorp.com', 30, 'mx3.ekorp.com'])
    packerExpectedResult = \
                b'\x08ekit-inc\x03com\x00\x00\x0f\x00\x01\x00\x01Q\x80\x00'+\
                b'\x0e\x00\n\x03mx1\x05ekorp\xc0\t\x00\x00\x0f\x00\x01\x00'+\
                b'\x01Q\x80\x00\x08\x00\x14\x03mx2\xc0\x1e\x00\x00\x0f\x00'+\
                b'\x01\x00\x01Q\x80\x00\x08\x00\x1e\x03mx3\xc0\x1e'

class testPackingOfNS(PackerTestCase):
    "addNS(self, name, klass, ttl, nsdname)"
    def doPack(self, p):
        p.addNS('ekit-inc.com', DNS.Class.IN, 86400, 'ns1.ekorp.com')
    def doUnpack(self, u):
        return u.getNSdata()
    unpackerExpectedResult = (('ekit-inc.com', 2, 1, 86400), 'ns1.ekorp.com')
    packerExpectedResult = b'\x08ekit-inc\x03com\x00\x00\x02\x00\x01\x00\x01Q\x80\x00\x0c\x03ns1\x05ekorp\xc0\t'

class testPackingOfPTR(PackerTestCase):
    "addPTR(self, name, klass, ttl, ptrdname)"
    def doPack(self, p):
        p.addPTR('www.ekit-inc.com', DNS.Class.IN, 3600, 'www-real01.ekorp.com')
    def doUnpack(self, u):
        return u.getPTRdata()
    unpackerExpectedResult = (('www.ekit-inc.com', 12, 1, 3600), 'www-real01.ekorp.com')
    packerExpectedResult = b'\x03www\x08ekit-inc\x03com\x00\x00\x0c\x00\x01\x00\x00\x0e\x10\x00\x13\nwww-real01\x05ekorp\xc0\r'

class testPackingOfSOA(PackerTestCase):
    """addSOA(self, name, klass, ttl, mname,
           rname, serial, refresh, retry, expire, minimum)"""
    def doPack(self, p):
        p.addSOA('ekit-inc.com', DNS.Class.IN, 3600, 'ns1.ekorp.com',
                 'hostmaster.ekit-inc.com', 2002020301, 100, 200, 300, 400)
    def doUnpack(self, u):
        return u.getSOAdata()
    unpackerExpectedResult = (('ekit-inc.com', 6, 1, 3600), ('ns1.ekorp.com', 'hostmaster', ('serial', 2002020301), ('refresh ', 100, '1 minutes'), ('retry', 200, '3 minutes'), ('expire', 300, '5 minutes'), ('minimum', 400, '6 minutes')))
    packerExpectedResult = b'\x08ekit-inc\x03com\x00\x00\x06\x00\x01\x00\x00\x0e\x10\x00,\x03ns1\x05ekorp\xc0\t\nhostmaster\x00wTg\xcd\x00\x00\x00d\x00\x00\x00\xc8\x00\x00\x01,\x00\x00\x01\x90'


class testPackingOfA(PackerTestCase):
    "addA(self, name, klass, ttl, address)"
    def doPack(self, p):
        p.addA('www02.ekit.com', DNS.Class.IN, 86400, '192.168.10.2')
    def doUnpack(self, u):
        return u.getAdata()
    unpackerExpectedResult = (('www02.ekit.com', 1, 1, 86400), '192.168.10.2')
    packerExpectedResult = b'\x05www02\x04ekit\x03com\x00\x00\x01\x00\x01\x00\x01Q\x80\x00\x04\xc0\xa8\n\x02'

class testPackingOfA2(PackerTestCase):
    "addA(self, name, ttl, address)"
    def doPack(self, p):
        p.addA('www.ekit.com', DNS.Class.IN, 86400, '10.98.1.0')
    def doUnpack(self, u):
        return u.getAdata()
    unpackerExpectedResult = (('www.ekit.com', 1, 1, 86400), '10.98.1.0')
    packerExpectedResult = b'\x03www\x04ekit\x03com\x00\x00\x01\x00\x01\x00\x01Q\x80\x00\x04\nb\x01\x00'

class testPackingOfA3(PackerTestCase):
    "addA(self, name, ttl, address)"
    def doPack(self, p):
        p.addA('www.zol.com', DNS.Class.IN, 86400, '192.168.10.4')
        p.addA('www.zol.com', DNS.Class.IN, 86400, '192.168.10.3')
        p.addA('www.zol.com', DNS.Class.IN, 86400, '192.168.10.2')
        p.addA('www.zol.com', DNS.Class.IN, 86400, '192.168.10.1')
    def doUnpack(self, u):
        u1,d1,u2,d2,u3,d3,u4=u.getAdata(),u.getRRheader(),u.getAdata(),u.getRRheader(),u.getAdata(),u.getRRheader(),u.getAdata()
        return u1,u2,u3,u4
    unpackerExpectedResult = (('www.zol.com', 1, 1, 86400), ('192.168.10.4', '192.168.10.3', '192.168.10.2', '192.168.10.1'))
    packerExpectedResult = b'\x03www\x03zol\x03com\x00\x00\x01\x00\x01\x00\x01Q\x80\x00\x04\xc0\xa8\n\x04\x00\x00\x01\x00\x01\x00\x01Q\x80\x00\x04\xc0\xa8\n\x03\x00\x00\x01\x00\x01\x00\x01Q\x80\x00\x04\xc0\xa8\n\x02\x00\x00\x01\x00\x01\x00\x01Q\x80\x00\x04\xc0\xa8\n\x01'

class testPackingOfTXT(PackerTestCase):
    "addTXT(self, name, klass, ttl, list)"
    def doPack(self, p):
        p.addTXT('ekit-inc.com', DNS.Class.IN, 3600, 'this is a text record')
    def doUnpack(self, u):
        return u.getTXTdata()
    packerExpectedResult = b'\x08ekit-inc\x03com\x00\x00\x10\x00\x01\x00\x00\x0e\x10\x00\x16\x15this is a text record'
    unpackerExpectedResult = (('ekit-inc.com', 16, 1, 3600), [b'this is a text record'])

# check what the maximum/minimum &c of TXT records are.
class testPackingOfTXT2(PackerTestCase):
    "addTXT(self, name, klass, ttl, list)"
    def doPack(self, p):
        f = lambda p=p:p.addTXT('ekit-inc.com', DNS.Class.IN, 3600, 'the quick brown fox jumped over the lazy brown dog\n'*20)
        self.assertRaises(ValueError, f)
        return TestCompleted
    doUnpack = None

class testPackingOfAAAAText(PackerTestCase):
    "addAAAA(self, name, klass, ttl, address)"
    def setUp(self):
        self.RRpacker = DNS.Lib.RRpacker
        self.RRunpacker = DNS.Lib.RRunpackerText
        
    def doPack(self, p):
        addAAAA(p, 'google.com', DNS.Class.IN, 4, '2607:f8b0:4005:802::1005')
    def doUnpack(self, u):
        r = u.getAAAAdata()
        return r
    packerExpectedResult = b'\x06google\x03com\x00\x00\x1c\x00\x01\x00\x00\x00\x04\x00\x10&\x07\xf8\xb0@\x05\x08\x02\x00\x00\x00\x00\x00\x00\x10\x05'
    unpackerExpectedResult = (('google.com', DNS.Type.AAAA, DNS.Class.IN, 4), '2607:f8b0:4005:802::1005')
    
class testPackingOfAAAABinary(PackerTestCase):
    "addAAAA(self, name, klass, ttl, address)"
    def setUp(self):
        self.RRpacker = DNS.Lib.RRpacker
        self.RRunpacker = DNS.Lib.RRunpackerBinary
        
    def doPack(self, p):
        addAAAA(p, 'google.com', DNS.Class.IN, 4, '2607:f8b0:4005:802::1005')
    def doUnpack(self, u):
        self.assertFalse(hasattr(u, "getAAAAdata"))
        r = u.getbytes(16)
        return r
    packerExpectedResult = b'\x06google\x03com\x00\x00\x1c\x00\x01\x00\x00\x00\x04\x00\x10&\x07\xf8\xb0@\x05\x08\x02\x00\x00\x00\x00\x00\x00\x10\x05'
    unpackerExpectedResult = (('google.com', DNS.Type.AAAA, DNS.Class.IN, 4), b'&\x07\xf8\xb0@\x05\x08\x02\x00\x00\x00\x00\x00\x00\x10\x05')
    
class testPackingOfAAAAInteger(PackerTestCase):
    "addAAAA(self, name, klass, ttl, address)"
    def setUp(self):
        self.RRpacker = DNS.Lib.RRpacker
        self.RRunpacker = DNS.Lib.RRunpackerInteger
            
    def doPack(self, p):
        addAAAA(p, 'google.com', DNS.Class.IN, 4, '2607:f8b0:4005:802::1005')
    def doUnpack(self, u):
        r = u.getAAAAdata()
        return r
    packerExpectedResult = b'\x06google\x03com\x00\x00\x1c\x00\x01\x00\x00\x00\x04\x00\x10&\x07\xf8\xb0@\x05\x08\x02\x00\x00\x00\x00\x00\x00\x10\x05'
    unpackerExpectedResult = (('google.com', DNS.Type.AAAA, DNS.Class.IN, 4), 50552053919387978162022445795852161029)

def addAAAA(p, name, klass, ttl, address):
    """Add AAAA record to a packer.
    """
    addr_buf = socket.inet_pton(socket.AF_INET6, address)
    p.addRRheader(name, DNS.Type.AAAA, klass, ttl)
    p.buf = p.buf + addr_buf
    p.endRR()
    return p

#class testPackingOfQuestion(PackerTestCase):
#    "addQuestion(self, qname, qtype, qclass)"
#    def doPack(self, p):
#        self.assertEquals(0,"NotImplemented")

def test_suite():
    from unittest import TestLoader
    return TestLoader().loadTestsFromName(__name__)

if __name__ == "__main__":
    unittest.main()
