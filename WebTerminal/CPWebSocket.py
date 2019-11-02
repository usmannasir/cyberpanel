import os
import asyncio
import websockets
import paramiko
import json
import ssl


class WebSocketServer():

    def loadPublicKey(self):
        pubkey = '/root/.ssh/cyberpanel.pub'

        data = open(pubkey, 'r').read()

        authFile = '/root/.ssh/authorized_keys'

        authData = open(authFile, 'r').read()

        checker = 1

        if authData.find(data) > -1:
            checker = 0

        if checker:
            writeToFile = open(authFile, 'a')
            writeToFile.writelines(data)
            writeToFile.close()


    def __init__(self, websocket, path):
        self.websockets = websocket
        self.path = path
        self.sshclient = paramiko.SSHClient()
        self.sshclient.load_system_host_keys()
        self.sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        k = paramiko.RSAKey.from_private_key_file('/root/.ssh/cyberpanel')

        ## Load Public Key
        self.loadPublicKey()

        self.sshclient.connect('127.0.0.1', 22, username='root', pkey=k)
        self.shell = self.sshclient.invoke_shell(term='xterm')
        self.shell.settimeout(0)
        self.verifyPath = ''

    async def consumer_handler(self):
        try:
            async for message in self.websockets:
                await self.sendData(message)
        except:
            print(self.verifyPath)
            os.remove(self.verifyPath)

    async def producer_handler(self):
        try:
            while True:
                message = await self.recvData()
                if os.path.exists(self.verifyPath):
                    await self.websockets.send(message)
                else:
                    await self.websockets.send('Authentication failed.')
        except:
            print(self.verifyPath)
            os.remove(self.verifyPath)

    async def recvData(self):
        try:
            print ('recvData')
            try:
                while True:
                    if self.shell.recv_ready():
                        return self.shell.recv(9000).decode("utf-8")
                    else:
                        await asyncio.sleep(0.1)
                        continue
            except:
                pass
        except:
            print(self.verifyPath)
            os.remove(self.verifyPath)

    async def sendData(self, message):
        try:
            print ('sendData')
            print (str(message))
            try:
                data = json.loads(message)
                if str(message).find('"tp":"init"') > -1:
                    self.verifyPath = str(data['data']['verifyPath'])
                else:
                    if os.path.exists(self.verifyPath):
                        self.shell.send(str(data['data']))
            except:
                pass
        except:
            print(self.verifyPath)
            os.remove(self.verifyPath)

    @staticmethod
    async def initialize(websocket, path):
        try:
            webshell = WebSocketServer(websocket, path)

            consumer_task = asyncio.ensure_future(
                webshell.consumer_handler())
            producer_task = asyncio.ensure_future(
                webshell.producer_handler())
            done, pending = await asyncio.wait(
                [consumer_task, producer_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
        except:
            print(webshell.verifyPath)
            os.remove(webshell.verifyPath)


def main():
    pidfile = '/usr/local/CyberCP/WebTerminal/pid'
    machineIP = open('/etc/cyberpanel/machineIP', 'r').read()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('/usr/local/lscp/conf/cert.pem', '/usr/local/lscp/conf/key.pem')
    start_server = websockets.serve(WebSocketServer.initialize, machineIP, 5678, ssl=context)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

    writeToFile = open(pidfile, 'r')
    writeToFile.write(str(os.getpid()))
    writeToFile.close()




if __name__ == "__main__":
    main()