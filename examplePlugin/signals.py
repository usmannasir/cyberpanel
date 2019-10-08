from django.dispatch import receiver
from django.http import HttpResponse
from websiteFunctions.signals import postWebsiteDeletion
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging

# This plugin respond to an event after CyberPanel core finished deleting a website.
# Original request object is passed, body can be accessed with request.body.

# If any Event handler returns a response object, CyberPanel will stop further processing and returns your response to browser.
# To continue processing just return 200 from your events handlers.

@receiver(postWebsiteDeletion)
def rcvr(sender, **kwargs):
    request = kwargs['request']
    logging.writeToFile('Hello World from Example Plugin.')
    return HttpResponse('Hello World from Example Plugin.')
