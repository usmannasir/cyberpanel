#!/usr/local/CyberCP/bin/python2
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import threading as multi
from CyberTronLogger import CyberTronLogger as logger
from inspect import stack
from shlex import split
from subprocess import call,CalledProcessError
from os.path import join
from random import randint
from logLevel import logLevel
from ipManagement.models import IPAddresses
from packages.models import VMPackage as Package
from django.db.models import Max
import CyberTronAPI.randomPassword as randomPassword
from vpsManagement.models import VPS
from loginSystem.models import Administrator
from CyberTronAPI.virtualMachineAPIKVM import virtualMachineAPI


def setupVMDisk():

    command = 'sudo virt-builder centos-7.2 -o /var/lib/libvirt/images/199.241.188.139.qcow2 --size 100G --root-password password:9xvps --upload /home/cyberpanel/ifcfg-ens384536:/etc/sysconfig/network-scripts/ifcfg-eth0 --upload /home/cyberpanel/network_62835:/etc/sysconfig/network --upload /home/cyberpanel/resolv_80440:/etc/resolv.conf'
    result = call(split(command))

setupVMDisk()