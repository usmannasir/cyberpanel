import tldextract

ext = tldextract.extract('http://forums.bbc.co.uk')

print ext.subdomain
print ext.domain
print ext.suffix