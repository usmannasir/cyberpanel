#!/usr/bin/env sh
# shellcheck disable=SC2034
dns_myapi_info='CyberPanel script for ACME to add records to PDNS
 A sample custom DNS API script.
Domains: example.com
Site: github.com/acmesh-official/acme.sh/wiki/DNS-API-Dev-Guide
Docs: github.com/acmesh-official/acme.sh/wiki/dnsapi#dns_duckdns
Options:
 MYAPI_Token API Token. Get API Token from https://example.com/api/. Optional.
Issues: github.com/usmannasir/cyberpanel
Author: Neil Pang <usman@cyberpersons.com>
'

# This file name is "dns_myapi.sh"
# So, here must be a method dns_myapi_add()
# Which will be called by acme.sh to add the txt record to your API system.
# Returns 0 means success, otherwise error.

########  Public functions #####################

# Please Read this guide first: https://github.com/acmesh-official/acme.sh/wiki/DNS-API-Dev-Guide

# Usage: dns_myapi_add _acme-challenge.www.domain.com "XKrxpRBosdIKFzxW_CT3KLZNf6q0HG9i01zxXp5CPBs"
dns_cyberpanel_add() {
  fulldomain=$1
  txtvalue=$2
  _info "Using CyberPanel ACME API"
  _debug fulldomain "$fulldomain"
  _debug txtvalue "$txtvalue"
  _info "cyberpanel createDNSRecord --domainName $fulldomain --name $fulldomain --recordType TXT --value $txtvalue --priority 0 --ttl 3600"

  cyberpanel createDNSRecord --domainName $fulldomain --name $fulldomain --recordType TXT --value $txtvalue --priority 0 --ttl 3600

  return 0
}

# Usage: fulldomain txtvalue
# Remove the txt record after validation.
dns_cyberpanel_rm() {
  fulldomain=$1
  txtvalue=$2
  _info "Using myapi"
  _debug fulldomain "$fulldomain"
  _debug txtvalue "$txtvalue"

  return 0
}

####################  Private functions below ##################################
# You can add private helper functions here if needed