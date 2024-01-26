#
# import imaplib
# import getpass
# from email import message_from_string
#
# # IMAP server settings
# imap_server = 'mail.wpmautic.net'
# imap_port = 993
#
# # User credentials
# email_address = 'usman@wpmautic.net'
# password = getpass.getpass("Enter your email password: ")
#
# # Connect to the IMAP server
# mail = imaplib.IMAP4_SSL(imap_server, imap_port)
#
# # Log in to the mailbox
# mail.login(email_address, password)
#
# # Select the INBOX
# mail.select("inbox")
#
# # Search for all emails in the INBOX
# result, data = mail.search(None, "ALL")
# email_ids = data[0].split()
#
# # Fetch and print header information for each email
# for email_id in email_ids:
#     result, message_data = mail.fetch(email_id, "(BODY[HEADER.FIELDS (FROM TO SUBJECT DATE)])")
#     raw_email = message_data[0][1].decode('utf-8')
#     msg = message_from_string(raw_email)
#     print(f"Email ID: {email_id}")
#     print(f"From: {msg['From']}")
#     print(f"To: {msg['To']}")
#     print(f"Subject: {msg['Subject']}")
#     print(f"Date: {msg['Date']}")
#     print("-" * 30)
#
# # Logout
# mail.logout()
#
# # from cryptography import x509
# # from cryptography.hazmat.backends import default_backend
# #
# # def get_domains_covered(cert_path):
# #     with open(cert_path, 'rb') as cert_file:
# #         cert_data = cert_file.read()
# #         cert = x509.load_pem_x509_certificate(cert_data, default_backend())
# #
# #         # Check for the Subject Alternative Name (SAN) extension
# #         san_extension = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
# #
# #         if san_extension:
# #             # Extract and print the domains from SAN
# #             san_domains = san_extension.value.get_values_for_type(x509.DNSName)
# #             return san_domains
# #         else:
# #             # If SAN is not present, return the Common Name as a fallback
# #             return [cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value]
# #
# # # Example usage
# # cert_path = '/etc/letsencrypt/live/cyberplanner.io/fullchain.pem'
# # domains_covered = get_domains_covered(cert_path)
# #
# # print("Domains covered by the certificate:")
# # for domain in domains_covered:
# #     print(domain)
