import OpenSSL
from datetime import datetime
filePath = '/etc/letsencrypt/live/%s/fullchain.pem' % ('hello.com')
x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                       open(filePath, 'r').read())
expireData = x509.get_notAfter().decode('ascii')
finalDate = datetime.strptime(expireData, '%Y%m%d%H%M%SZ')
print x509.get_issuer().get_components()[1][1]