# The world is a prison for the believer.

from django.dispatch import Signal

## This event is fired before CyberPanel core load the create database template, this special event is used
## to create a beautiful names official plugin. Actual FTP account creation happens with event named preSubmitDBCreation and postSubmitDBCreation.
preCreateDatabase = Signal(providing_args=["request"])

## See preCreateDatabase
postCreateDatabase = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start creation of a database.
preSubmitDBCreation = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished creation of a database.
postSubmitDBCreation = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start deletion of a database
preSubmitDatabaseDeletion = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished deletion of a database.
postSubmitDatabaseDeletion = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start to change a database password.
preChangePassword = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished changing database password.
postChangePassword = Signal(providing_args=["request", "response"])