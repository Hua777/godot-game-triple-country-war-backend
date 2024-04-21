from twisted.internet import protocol


class SimpleSocketProtocol(protocol.Protocol):
    def connectionMade(self):
        self.transport.write(b"Hello, Socket!")

    def dataReceived(self, data):
        print("Received data:", data.decode())

    def connectionLost(self, reason):
        print("Connection lost.")


def install(factory: protocol.ServerFactory):
    factory.protocol = SimpleSocketProtocol
