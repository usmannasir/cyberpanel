import signal
import sys
import ssl
from SimpleWebSocketServer import WebSocket, SimpleSSLWebSocketServer
import paramiko
import os
import json
import threading as multi
import time

class SSHServer(multi.Thread):
    OKGREEN = '\033[92m'
    ENDC = '\033[0m'

    DEFAULT_PORT = 22

    @staticmethod
    def findSSHPort():
        try:
            sshData = open('/etc/ssh/sshd_config', 'r').readlines()

            for items in sshData:
                if items.find('Port') > -1:
                    if items[0] == 0:
                        pass
                    else:
                        SSHServer.DEFAULT_PORT = int(items.split(' ')[1])
        except:
            pass

    def loadPublicKey(self):
        pubkey = '/root/.ssh/cyberpanel.pub'
        data = open(pubkey, 'r').read()
        authFile = '/root/.ssh/authorized_keys'

        checker = 1

        try:
            authData = open(authFile, 'r').read()
            if authData.find(data) > -1:
                checker = 0
        except:
            pass

        if checker:
            writeToFile = open(authFile, 'a')
            writeToFile.writelines(data)
            writeToFile.close()

    def __init__(self, websocket):
        multi.Thread.__init__(self)
        self.sshclient = paramiko.SSHClient()
        self.sshclient.load_system_host_keys()
        self.sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        k = paramiko.RSAKey.from_private_key_file('/root/.ssh/cyberpanel')

        ## Load Public Key
        self.loadPublicKey()

        self.sshclient.connect('127.0.0.1', SSHServer.DEFAULT_PORT, username='root', pkey=k)
        self.shell = self.sshclient.invoke_shell(term='xterm')
        self.shell.settimeout(0)

        self.websocket = websocket
        self.color = 0

    def recvData(self):
        while True:
            try:
                if self.websocket.running:
                    if os.path.exists(self.websocket.verifyPath):
                        if self.websocket.filePassword == self.websocket.password:
                            if self.shell.recv_ready():
                                if self.color == 0:
                                    text = '%sEnjoy your accelerated Internet by CyberPanel and LiteSpeed%s' % (SSHServer.OKGREEN, SSHServer.ENDC)
                                    nText = 'Enjoy your accelerated Internet by CyberPanel'
                                    self.websocket.sendMessage(self.shell.recv(9000).decode("utf-8").replace(nText, text))
                                    self.color = 1
                                else:
                                    self.websocket.sendMessage(self.shell.recv(9000).decode("utf-8"))
                            else:
                                time.sleep(0.01)
                else:
                    return 0
            except BaseException as msg:
                time.sleep(0.1)

    def run(self):
        try:
            self.recvData()
        except BaseException as msg:
            print((str(msg)))


class WebTerminalServer(WebSocket):

   def handleMessage(self):
       try:
           data = json.loads(self.data)
           if str(self.data).find('"tp":"init"') > -1:
               self.verifyPath = str(data['data']['verifyPath'])
               self.password = str(data['data']['password'])
               self.filePassword = open(self.verifyPath, 'r').read()
           else:
               if os.path.exists(self.verifyPath):
                   if self.filePassword == self.password:
                    self.shell.send(str(data['data']))
       except:
           pass

   def handleConnected(self):
      self.running = 1
      self.sh = SSHServer(self)
      self.shell = self.sh.shell
      self.sh.start()

   def handleClose(self):
      try:
          os.remove(self.verifyPath)
          self.running = 0
      except:
          pass


if __name__ == "__main__":
   pidfile = '/usr/local/CyberCP/WebTerminal/pid'

   writeToFile = open(pidfile, 'w')
   writeToFile.write(str(os.getpid()))
   writeToFile.close()

   SSHServer.findSSHPort()

   server = SimpleSSLWebSocketServer('0.0.0.0', '5678', WebTerminalServer,  '/usr/local/lscp/conf/cert.pem', '/usr/local/lscp/conf/key.pem', version=ssl.PROTOCOL_TLSv1)

   def close_sig_handler(signal, frame):
      server.close()
      sys.exit()

   signal.signal(signal.SIGINT, close_sig_handler)
   server.serveforever()