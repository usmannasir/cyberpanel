import re


verifer = re.compile(r'[a-zA-Z0-9_-]+')

if verifer.match('Helloworld'):
    print ('hello world')
else:
    print('not hello world')