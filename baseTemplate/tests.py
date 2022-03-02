import requests



ab = {'package': 'helo world', 'Themename': 'blue-green-theme'}

url= "https://raw.githubusercontent.com/usmannasir/CyberPanel-Themes/main/%s/design.css"%ab['Themename']
#url= "https://api.github.com/repos/usmannasir/CyberPanel-Themes/git/commits/def351a6eb4c103fb2dd2acf52396d4ef6111eee"


res=requests.get(url)
# sha=res.json()[0]['sha']
print(res.text)

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
