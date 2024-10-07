from django.dispatch import receiver
from django.shortcuts import redirect
from firewall.signals import preFirewallHome, preCSF

@receiver(preFirewallHome)
def csfFirewallHome(sender, **kwargs):
    request = kwargs['request']
    return redirect('/configservercsf/')

@receiver(preCSF)
def csfCSF(sender, **kwargs):
    request = kwargs['request']
    return redirect('/configservercsf/')
