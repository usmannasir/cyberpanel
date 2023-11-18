import requests
import json



ab = {'package': 'helo world', 'Themename': 'blue-green-theme'}

url= "http://cyberpanel.net/version.txt"
#url= "https://api.github.com/repos/usmannasir/CyberPanel-Themes/git/commits/def351a6eb4c103fb2dd2acf52396d4ef6111eee"


res=requests.get(url)
# sha=res.json()[0]['sha']
a= res.json()['version']

print(a)
print(res)

u = "https://api.github.com/repos/usmannasir/cyberpanel/commits?sha=v%s"%a
r= requests.get(u)

print(r.text)
# l ="https://api.github.com/repos/usmannasir/CyberPanel-Themes/git/trees/%s"%sha
# fres=requests.get(l)
#
# print(fres.json())
# # tott = len(fres.json()['tree'])
#
# finalData['tree']=[]
# for i in range(tott):
#     if(fres.json()['tree'][i]['type']=="tree"):
#         finalData['tree'].append(fres.json()['tree'][i]['path'])
#
# print(finalData['tree'])
