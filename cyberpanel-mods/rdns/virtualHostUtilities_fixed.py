# Fixed OnBoardingHostName function sections for CyberPanel 2.4.4
# Replace the relevant sections in /usr/local/CyberCP/plogical/virtualHostUtilities.py
#
# Section 1: Replace the rDNS lookup section (around line 119-137)
# Section 2: Replace the domain validation section (around line 333-343)

# ============================================================================
# SECTION 1: Replace lines 119-137 in OnBoardingHostName function
# ============================================================================

        ### if skipRDNSCheck == 1, it means we need to skip checking for rDNS
        if skipRDNSCheck:
            ### When skipping rDNS check, include both current hostname and the domain being set up
            ### This ensures both code paths work correctly
            rDNS = [CurrentHostName, Domain]
        else:
            try:
                rDNS = mailUtilities.reverse_dns_lookup(serverIP)
                # Check if rDNS lookup returned empty results (indicating lookup failure)
                if not rDNS or len(rDNS) == 0:
                    message = f'Failed to perform reverse DNS lookup for server IP {serverIP}. The DNS lookup service may be unavailable or the IP address may not have rDNS configured. Please verify your rDNS settings with your hosting provider or check the "Skip rDNS/PTR Check" option if you do not need email services. [404]'
                    logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, message)
                    logging.CyberCPLogFileWriter.writeToFile(message)
                    return 0
            except Exception as e:
                message = f'Failed to perform reverse DNS lookup for server IP {serverIP}: {str(e)}. Please verify your rDNS settings with your hosting provider or check the "Skip rDNS/PTR Check" option if you do not need email services. [404]'
                logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, message)
                logging.CyberCPLogFileWriter.writeToFile(message)
                return 0

# ============================================================================
# SECTION 2: Replace lines 333-343 in OnBoardingHostName function
# ============================================================================

            #first check if hostname is already configured as rDNS, if not return error

            # Validate that we have rDNS results before checking
            if not rDNS or len(rDNS) == 0:
                message = f'Reverse DNS lookup failed for server IP {serverIP}. Unable to verify if domain "{Domain}" is configured as rDNS. Please check your rDNS configuration with your hosting provider or select "Skip rDNS/PTR Check" if you do not need email services. [404]'
                print(message)
                logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, message)
                logging.CyberCPLogFileWriter.writeToFile(message)
                config['hostname'] = Domain
                config['onboarding'] = 3
                config['skipRDNSCheck'] = skipRDNSCheck
                admin.config = json.dumps(config)
                admin.save()
                return 0

            if Domain not in rDNS:
                rDNS_list_str = ', '.join(rDNS) if rDNS else 'none'
                message = f'Domain "{Domain}" that you have provided is not configured as rDNS for your server IP {serverIP}. Current rDNS records: {rDNS_list_str}. Please configure rDNS (PTR record) for your IP address to point to "{Domain}" with your hosting provider, or select "Skip rDNS/PTR Check" if you do not need email services. [404]'
                print(message)
                logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, message)
                logging.CyberCPLogFileWriter.writeToFile(message)
                config['hostname'] = Domain
                config['onboarding'] = 3
                config['skipRDNSCheck'] = skipRDNSCheck
                admin.config = json.dumps(config)
                admin.save()
                return 0

