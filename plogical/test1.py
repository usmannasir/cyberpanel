# import socket
#
# def reverse_dns_lookup(ip_address):
#     try:
#         host_name, _, _ = socket.gethostbyaddr(ip_address)
#         return host_name
#     except socket.herror as e:
#         # Handle errors, e.g., if reverse DNS lookup fails
#         return None
#
# # Example usage
# ip_address_to_check = "95.217.248.69"
# result = reverse_dns_lookup(ip_address_to_check)
#
# if result:
#     print(f"Reverse DNS lookup for {ip_address_to_check}: {result}")
# else:
#     print(f"Reverse DNS lookup failed for {ip_address_to_check}")
#
#
# import socket
#
# def reverse_dns_lookup_bypass_cache(ip_address):
#     try:
#         # Use getnameinfo to bypass DNS cache
#         host_name, _ = socket.getnameinfo((ip_address, 0), socket.NI_NAMEREQD)
#         return host_name
#     except socket.herror as e:
#         # Handle errors, e.g., if reverse DNS lookup fails
#         return None
#
# # Example usage
# ip_address_to_check = "95.217.248.69"
# result = reverse_dns_lookup_bypass_cache(ip_address_to_check)
#
# if result:
#     print(f"Reverse DNS lookup for {ip_address_to_check}: {result}")
# else:
#     print(f"Reverse DNS lookup failed for {ip_address_to_check}")