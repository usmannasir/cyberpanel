# The world is a prison for the believer.

from django.dispatch import Signal

## This event is fired before CyberPanel core load template for create backup page.
preBackupSite = Signal(providing_args=["request"])

## This event is fired after CyberPanel core load template for create backup page.
postBackupSite = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core load template for restore backup page.
preRestoreSite = Signal(providing_args=["request"])

## This event is fired after CyberPanel core load template for restore backup page.
postRestoreSite = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start creating backup of a website
preSubmitBackupCreation = Signal(providing_args=["request"])

## This event is fired before CyberPanel core starts to load status of backup started earlier througb submitBackupCreation
preBackupStatus = Signal(providing_args=["request"])

## This event is fired after CyberPanel core has loaded backup status
postBackupStatus = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start deletion of a backup
preDeleteBackup = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished the backup deletion
postDeleteBackup = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start restoring a backup.
preSubmitRestore = Signal(providing_args=["request"])

## This event is fired before CyberPanel core starts to add a remote backup destination
preSubmitDestinationCreation = Signal(providing_args=["request"])

## This event is fired after CyberPanel core is finished adding remote backup destination
postSubmitDestinationCreation = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core starts to delete a backup destination
preDeleteDestination = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished deleting a backup destination
postDeleteDestination = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start adding a backup schedule
preSubmitBackupSchedule = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished adding a backup schedule
postSubmitBackupSchedule = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start the deletion of backup schedule
preScheduleDelete = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished the deletion of backup schedule
postScheduleDelete = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core star the remote backup process
preSubmitRemoteBackups = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished remote backup process
postSubmitRemoteBackups = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core star the remote backup process
preStarRemoteTransfer = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished remote backup process
postStarRemoteTransfer = Signal(providing_args=["request", "response"])

## This event is fired before CyberPanel core start restore of remote backups
preRemoteBackupRestore = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished restoring remote backups in local server
postRemoteBackupRestore = Signal(providing_args=["request", "response"])
