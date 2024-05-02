from socket_pkg.socket_user import SocketUser


class SocketUserForRoomInterface:
    def __init__(self, socket_user: SocketUser) -> None:
        self.socket_user = socket_user
        self.ready: bool = False

    def on_open(self):
        pass

    def on_request(self, msg_id: str, command: str, info: dict):
        pass

    def on_response(self, msg_id: str, command: str, info: dict):
        pass

    def on_close(self):
        pass

    def send_ack(self, command: str, msg_id: str, info: dict):
        self.socket_user.send_ack(command, msg_id, info)

    def send_command(self, command: str, info: dict):
        self.socket_user.send_command(command, info)
