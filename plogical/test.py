LaterCommand = """awk '/access_token/ {print $3}' | sed 's/[",]//g'"""
print(LaterCommand)