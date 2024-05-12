import json
import uuid

from autobahn.twisted.websocket import WebSocketServerProtocol

from game.socket_user_for_standard_room import SocketUserForStandardRoom

from http_pkg.http_user import save_user_online_tag


def parse_msg(data: bytes) -> tuple[str, str, str, dict]:
    data_decode = data.decode("utf-8")
    print("[websocket] received message:", data_decode)
    value = json.loads(data_decode)
    return (value["msg_id"], value["mode"], value["command"], value)


class SocketUser(WebSocketServerProtocol):
    def __init__(self) -> None:
        super().__init__()
        self.account: str = None
        self.plugins = [SocketUserForStandardRoom(self)]

    def onConnect(self, request):
        self.host = request.host

    def onOpen(self):
        for plugin in self.plugins:
            plugin.on_open()

    def onMessage(self, payload: bytes, isBinary):
        (msg_id, mode, command, info) = parse_msg(payload)
        if mode == "request":
            if command == "online":
                self.account = info["account"]
                users[self.account] = self
                save_user_online_tag(self.account, self.host, True)
                self.send_ack(
                    "online",
                    msg_id,
                    {
                        "msg": "上线成功",
                    },
                )
            else:
                for plugin in self.plugins:
                    plugin.on_request(msg_id, command, info)
        elif mode == "response":
            for plugin in self.plugins:
                plugin.on_response(msg_id, command, info)

    def onClose(self, wasClean, code, reason):
        for plugin in self.plugins:
            plugin.on_close()
        if self.account is not None:
            print(f"[websocket] {self.account} exit game, reason: {reason}")
            del users[self.account]
            save_user_online_tag(self.account, self.host, False)

    def send_ack(self, command: str, msg_id: str, info: dict):
        if msg_id is not None:
            info["msg_id"] = msg_id
            info["mode"] = "response"
            info["command"] = command
            print(f"[websocket] ack message {info}")
            self.sendMessage(json.dumps(info, default=str).encode("utf-8"), False)

    def send_command(self, command: str, info: dict):
        info["msg_id"] = str(uuid.uuid4())
        info["mode"] = "request"
        info["command"] = command
        info["command"] = command
        print(f"[websocket] send message {info}")
        self.sendMessage(json.dumps(info, default=str).encode("utf-8"), False)


users: dict[str, SocketUser] = {}
