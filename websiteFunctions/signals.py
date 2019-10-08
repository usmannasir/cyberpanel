# The world is a prison for the believer.
## https://www.youtube.com/watch?v=DWfNYztUM1U

from django.dispatch import Signal

## This event is fired before CyberPanel core start creation of website
preWebsiteCreation = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished creation of website.
postWebsiteCreation = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start creation of child-domain
preDomainCreation = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished creation of child-domain.
postDomainCreation = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start deletion of website
preWebsiteDeletion = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished deletion of website
postWebsiteDeletion = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start deletion of child-domain
preDomainDeletion = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished deletion of child-domain
postDomainDeletion = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start suspension of website
preWebsiteSuspension = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished suspension of website
postWebsiteSuspension = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start suspension of website
preWebsiteModification = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished suspension of website
postWebsiteModification = Signal(providing_args=["request", "response"])


## This event is fired before CyberPanel core load website launcher
preDomain = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished loading website launcher
postDomain = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start saving changes to vhost conf
preSaveConfigsToFile = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished saving changes to vhost conf
postSaveConfigsToFile = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start saving changes to vhost rewrite file
preSaveRewriteRules = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished saving changes to vhost rewrite file
postSaveRewriteRules = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start saving custom SSL
preSaveSSL = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished saving saving custom SSL
postSaveSSL = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start changing php version of domain or website
preChangePHP = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished change php version of domain or website
postChangePHP = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start changing open_basdir status for domain or website
preChangeOpenBasedir = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished changing open_basdir status for domain or website
postChangeOpenBasedir = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start adding new cron
preAddNewCron = Signal(providing_args=["request"])

## This event is fired after CyberPanel core is finished adding new cron
postAddNewCron = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start removing cron
preRemCronbyLine = Signal(providing_args=["request"])

## This event is fired after CyberPanel core is finished removing cron
postRemCronbyLine = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start creating domain alias
preSubmitAliasCreation = Signal(providing_args=["request"])

## This event is fired after CyberPanel core is finished creating domain alias
postSubmitAliasCreation = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start deleting domain alais
preDelateAlias = Signal(providing_args=["request"])

## This event is fired after CyberPanel core is finished deleting domain alias
postDelateAlias = Signal(providing_args=["request", "response"])