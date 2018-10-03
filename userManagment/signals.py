from django.dispatch import receiver
from websiteFunctions.signals import postWebsiteDeletion

@receiver(postWebsiteDeletion)
def rcvr(sender, **kwargs):
    request = kwargs['request']
    return 200
