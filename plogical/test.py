hey = ['hey', 'aaa', 'aaa', 'adssad']
aaa='aaa'
print(type(hey))
print(type(aaa))
print(hasattr(hey, "__len__"))
print(hasattr(aaa, "__len__"))

if type(hey) == list:
    print('list')
else:
    print('hey not list')

if type(aaa) == list:
    print('aaa')
else:
    print('aaa not list')