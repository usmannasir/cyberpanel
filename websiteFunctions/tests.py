a = "/home/habibackup.ml/public_html/////"
DomainName ="newweb3.com"
abc = a.split("/")
wpexpath = abc[4]
newpath = '/home/%s/public_html/%s' % (DomainName, wpexpath)

if wpexpath != "":
    home = "0"
else:
    home = "1"
print(home)
