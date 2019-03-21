import subprocess


def installCertBot():
    cmd = []

    cmd.append("yum")
    cmd.append("-y")
    cmd.append("install")
    cmd.append("certbot")

    res = ProcessUtilities.executioner(cmd)


installCertBot()