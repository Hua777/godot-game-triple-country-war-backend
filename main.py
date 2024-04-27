from twisted.internet import reactor
from twisted.web import server, resource

from http_pkg import http_health, http_user, http_room
from socket_pkg.socket_main import TcbwSocketProtocol

from autobahn.twisted.websocket import WebSocketServerFactory

root = resource.Resource()
http_health.install(root)
http_user.install(root)
http_room.install(root)
site = server.Site(root)
reactor.listenTCP(8080, site)

factory = WebSocketServerFactory()
factory.protocol = TcbwSocketProtocol
reactor.listenTCP(8090, factory)

reactor.run()
