a = "/home/folderhabitk.ml/public_html/subfile/"
DomainName ="newweb3.com"
abc = a.split("/")
wpexpath = abc[4]


b=a.rstrip('/')
c= b.rstrip(wpexpath)
newpath = '/home/%s/public_html/%s' % (DomainName, wpexpath)

if wpexpath != "":
    home = "0"
else:
    home = "1"
print(wpexpath)
print(c)
