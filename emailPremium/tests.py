

stdout = "WARNING: apt does not have a stable CLI interface. Use with caution in scripts.rspamd/focal,now 1.9.4-2build4 amd64 [residual-config]"
a= stdout.find("installed")
if a != -1:
    print("1")
else:
    print("0")