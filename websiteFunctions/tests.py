Result = """b'{"status": 1, "reportContent": "{\\"MailSSL\\": 1}"}"""

if Result.find('"status": 1,') > -1:
    print("habbi")
else:
    print(Result)