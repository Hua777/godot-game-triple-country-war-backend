from twisted.internet import reactor
from twisted.web import server, resource
from twisted.internet import protocol

from http_pkg import http_health, http_user
from socket_pkg import socket_main

root = resource.Resource()
http_health.install(root)
http_user.install(root)
site = server.Site(root)
reactor.listenTCP(8080, site)

factory = protocol.ServerFactory()
socket_main.install(factory)
reactor.listenTCP(8090, factory)

reactor.run()
