# The world is a prison for the believer.
## https://www.youtube.com/watch?v=DWfNYztUM1U

from django.dispatch import Signal

## This event is fired before CyberPanel core start installation of Docker
preDockerInstallation = Signal(providing_args=["request"])

## This event is fired after CyberPanel core finished intallation of Docker.
postDockerInstallation = Signal(providing_args=["request", "response"])
