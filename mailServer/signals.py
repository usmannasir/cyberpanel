# The world is a prison for the believer.
## https://www.youtube.com/watch?v=DWfNYztUM1U

from django.dispatch import Signal

## This event is fired before CyberPanel core start creation of an email account.
preSubmitEmailCreation = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished creation of an email account.
postSubmitEmailCreation = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start deletion of an email account
preSubmitEmailDeletion = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished deletion of an email account
postSubmitEmailDeletion = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start deletion of email forwarding.
preSubmitForwardDeletion = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished deletion of email forwarding.
postSubmitForwardDeletion = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start creation of email forwarding.
preSubmitEmailForwardingCreation = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished creation of email forwarding.
postSubmitEmailForwardingCreation = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start changing password for email account.
preSubmitPasswordChange = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished changing password for email account.
postSubmitPasswordChange = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start generating dkim keys.
preGenerateDKIMKeys = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished generating dkim keys.
postGenerateDKIMKeys = Signal(providing_args=["request", "response"])