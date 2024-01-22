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

statusFile = '/home/cyberpanel/aASA'

TemFilePath = statusFile.split('panel/')[1]

try:
    print(TemFilePath)
    value = int(TemFilePath)
except BaseException as msg:
    print(str(msg))