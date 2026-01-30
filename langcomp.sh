# Create message files for all the languages
django-admin makemessages -l zh-Hans
django-admin makemessages -l bg
django-admin makemessages -l pt
django-admin makemessages -l ja
django-admin makemessages -l bs
django-admin makemessages -l el
django-admin makemessages -l ru
django-admin makemessages -l tr
django-admin makemessages -l es
django-admin makemessages -l fr
django-admin makemessages -l pl
django-admin makemessages -l vi
django-admin makemessages -l it
django-admin makemessages -l de
django-admin makemessages -l id
django-admin makemessages -l bn

# Translate the .po files

# Compile the message files
django-admin compilemessages
