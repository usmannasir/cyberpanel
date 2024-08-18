# The world is a prison for the believer.
## https://www.youtube.com/watch?v=DWfNYztUM1U

from django.dispatch import Signal

## This event is fired before CyberPanel core start creation of website
preWebsiteCreation = Signal()

## This event is fired after CyberPanel core finished creation of website.
postWebsiteCreation = Signal()

## This event is fired before CyberPanel core start creation of child-domain
preDomainCreation = Signal()

## This event is fired after CyberPanel core finished creation of child-domain.
postDomainCreation = Signal()

## This event is fired before CyberPanel core start deletion of website
preWebsiteDeletion = Signal()

## This event is fired after CyberPanel core finished deletion of website
postWebsiteDeletion = Signal()

## This event is fired before CyberPanel core start deletion of child-domain
preDomainDeletion = Signal()

## This event is fired after CyberPanel core finished deletion of child-domain
postDomainDeletion = Signal()

## This event is fired before CyberPanel core start suspension of website
preWebsiteSuspension = Signal()

## This event is fired after CyberPanel core finished suspension of website
postWebsiteSuspension = Signal()

## This event is fired before CyberPanel core start suspension of website
preWebsiteModification = Signal()

## This event is fired after CyberPanel core finished suspension of website
postWebsiteModification = Signal()


## This event is fired before CyberPanel core load website launcher
preDomain = Signal()

## This event is fired after CyberPanel core finished loading website launcher
postDomain = Signal()

## This event is fired before CyberPanel core start saving changes to vhost conf
preSaveConfigsToFile = Signal()

## This event is fired after CyberPanel core finished saving changes to vhost conf
postSaveConfigsToFile = Signal()

## This event is fired before CyberPanel core start saving changes to vhost rewrite file
preSaveRewriteRules = Signal()

## This event is fired after CyberPanel core finished saving changes to vhost rewrite file
postSaveRewriteRules = Signal()

## This event is fired before CyberPanel core start saving custom SSL
preSaveSSL = Signal()

## This event is fired after CyberPanel core finished saving saving custom SSL
postSaveSSL = Signal()

## This event is fired before CyberPanel core start changing php version of domain or website
preChangePHP = Signal()

## This event is fired after CyberPanel core finished change php version of domain or website
postChangePHP = Signal()

## This event is fired before CyberPanel core start changing open_basdir status for domain or website
preChangeOpenBasedir = Signal()

## This event is fired after CyberPanel core finished changing open_basdir status for domain or website
postChangeOpenBasedir = Signal()

## This event is fired before CyberPanel core start adding new cron
preAddNewCron = Signal()

## This event is fired after CyberPanel core is finished adding new cron
postAddNewCron = Signal()

## This event is fired before CyberPanel core start removing cron
preRemCronbyLine = Signal()

## This event is fired after CyberPanel core is finished removing cron
postRemCronbyLine = Signal()

## This event is fired before CyberPanel core start creating domain alias
preSubmitAliasCreation = Signal()

## This event is fired after CyberPanel core is finished creating domain alias
postSubmitAliasCreation = Signal()

## This event is fired before CyberPanel core start deleting domain alais
preDelateAlias = Signal()

## This event is fired after CyberPanel core is finished deleting domain alias
postDelateAlias = Signal()