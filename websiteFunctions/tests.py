a = "/home/newweb2.com/public_html/newweb2/"
DomainName ="newweb3.com"
abc = a.split("/")
wpexpath = abc[4]
newpath = '/home/%s/public_html/%s' % (DomainName, wpexpath)

print(newpath)
