# Fixed reverse_dns_lookup function for CyberPanel 2.4.4
# Replace the reverse_dns_lookup function in /usr/local/CyberCP/plogical/mailUtilities.py
# 
# Original function location: around line 1637
# This is the complete fixed function to replace the original

    @staticmethod
    def reverse_dns_lookup(ip_address):
        """
        Perform reverse DNS lookup for the given IP address using external DNS servers.
        
        Args:
            ip_address: The IP address to perform reverse DNS lookup on
            
        Returns:
            list: List of rDNS hostnames found, or empty list if lookup fails
        """
        try:
            import requests
            from requests.exceptions import RequestException, Timeout, ConnectionError

            # Fetch DNS server URLs with proper error handling
            try:
                fetchURLs = requests.get('https://cyberpanel.net/dnsServers.txt', timeout=10)
            except (ConnectionError, Timeout) as e:
                logging.CyberCPLogFileWriter.writeToFile(f'Failed to fetch DNS server list from cyberpanel.net: {str(e)}')
                return []
            except RequestException as e:
                logging.CyberCPLogFileWriter.writeToFile(f'Request error while fetching DNS server list: {str(e)}')
                return []

            if fetchURLs.status_code != 200:
                logging.CyberCPLogFileWriter.writeToFile(f'Failed to fetch DNS server list: HTTP {fetchURLs.status_code}')
                return []

            try:
                urls_data = fetchURLs.json()
                if 'urls' not in urls_data:
                    logging.CyberCPLogFileWriter.writeToFile('DNS server list response missing "urls" key')
                    return []
                urls = urls_data['urls']
            except (ValueError, KeyError) as e:
                logging.CyberCPLogFileWriter.writeToFile(f'Failed to parse DNS server list JSON: {str(e)}')
                return []

            if not isinstance(urls, list) or len(urls) == 0:
                logging.CyberCPLogFileWriter.writeToFile('DNS server list is empty or invalid')
                return []

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(f'DNS urls {urls}.')

            results = []
            successful_queries = 0

            # Query each DNS server
            for url in urls:
                try:
                    response = requests.get(f'{url}/index.php?ip={ip_address}', timeout=5)

                    if os.path.exists(ProcessUtilities.debugPath):
                        logging.CyberCPLogFileWriter.writeToFile(f'url to call {ip_address} is {url}')

                    if response.status_code == 200:
                        try:
                            data = response.json()

                            if os.path.exists(ProcessUtilities.debugPath):
                                logging.CyberCPLogFileWriter.writeToFile(f'response from dns system {str(data)}')

                            # Validate response structure
                            if not isinstance(data, dict):
                                logging.CyberCPLogFileWriter.writeToFile(f'Invalid response format from {url}: not a dictionary')
                                continue

                            if 'status' not in data:
                                logging.CyberCPLogFileWriter.writeToFile(f'Response from {url} missing "status" key')
                                continue

                            if data['status'] == 1:
                                # Validate results structure
                                if 'results' not in data or not isinstance(data['results'], dict):
                                    logging.CyberCPLogFileWriter.writeToFile(f'Response from {url} missing or invalid "results" key')
                                    continue

                                results_dict = data['results']
                                
                                # Safely extract results from different DNS servers
                                dns_servers = ['8.8.8.8', '1.1.1.1', '9.9.9.9']
                                for dns_server in dns_servers:
                                    if dns_server in results_dict:
                                        result_value = results_dict[dns_server]
                                        if result_value and result_value not in results:
                                            results.append(result_value)
                                
                                successful_queries += 1
                            else:
                                if os.path.exists(ProcessUtilities.debugPath):
                                    logging.CyberCPLogFileWriter.writeToFile(f'DNS server {url} returned status != 1: {data.get("status", "unknown")}')
                        except ValueError as e:
                            logging.CyberCPLogFileWriter.writeToFile(f'Failed to parse JSON response from {url}: {str(e)}')
                            continue
                        except KeyError as e:
                            logging.CyberCPLogFileWriter.writeToFile(f'Missing key in response from {url}: {str(e)}')
                            continue
                    else:
                        if os.path.exists(ProcessUtilities.debugPath):
                            logging.CyberCPLogFileWriter.writeToFile(f'DNS server {url} returned HTTP {response.status_code}')
                except Timeout as e:
                    logging.CyberCPLogFileWriter.writeToFile(f'Timeout while querying DNS server {url}: {str(e)}')
                    continue
                except ConnectionError as e:
                    logging.CyberCPLogFileWriter.writeToFile(f'Connection error while querying DNS server {url}: {str(e)}')
                    continue
                except RequestException as e:
                    logging.CyberCPLogFileWriter.writeToFile(f'Request error while querying DNS server {url}: {str(e)}')
                    continue
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f'Unexpected error while querying DNS server {url}: {str(e)}')
                    continue

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(f'rDNS result of {ip_address} is {str(results)} (successful queries: {successful_queries}/{len(urls)})')

            # Return results (empty list if no successful queries)
            return results
            
        except ImportError as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Failed to import requests library: {str(e)}')
            return []
        except BaseException as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Unexpected error in reverse_dns_lookup for IP {ip_address}: {str(e)}')
            return []

