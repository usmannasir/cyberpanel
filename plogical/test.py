import socket

def check_dns_record_socket(domain_name):
    """
    Queries the A record for a given domain name using the socket module.

    Args:
        domain_name (str): The domain name to query.

    Returns:
        The IP address as a string, or None if the record is not found.
    """
    try:
        # Query the A record
        result = socket.getaddrinfo(domain_name, None, socket.AF_INET)[0]

        # Return the IP address as a string
        return result[4][0]
    except (socket.gaierror, IndexError):
        # The domain does not exist or the record is not found
        return None


# Check the A record for google.com
result = check_dns_record_socket("wpmautic.net")
print(result) # Output: 216.58.194.174
