from twisted.internet import endpoints, reactor
from twisted.web import server, resource

from http_pkg import http_health, http_user, http_room, http_game
from socket_pkg.socket_user import SocketUser

from autobahn.twisted.websocket import WebSocketServerFactory

# HTTP Server

root = resource.Resource()
http_health.install(root)
http_user.install(root)
http_room.install(root)
http_game.install(root)
site = server.Site(root)

# ipv4
reactor.listenTCP(8080, site)

# ipv6
tcp6 = endpoints.TCP6ServerEndpoint(reactor, 8080, interface="::")
tcp6.listen(site)

# Socket Server

factory = WebSocketServerFactory()
factory.protocol = SocketUser
reactor.listenTCP(8090, factory)

# start

reactor.run()
