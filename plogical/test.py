import re

line = "usman.exampl.com"
matchObj = re.match( r'([\da-z\.-]+\.[a-z\.]{2,12}|[\d\.]+)([\/:?=&#]{1}[\da-z\.-]+)*[\/\?]?', line, re.M|re.I)

if matchObj:
    print line