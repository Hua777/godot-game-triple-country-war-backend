from socket_pkg.socket_user import SocketUser

from game.room_interface import RoomInterface


class SocketUserForRoomInterface:
    def __init__(self, socket_user: SocketUser) -> None:
        # Socket
        self.socket_user = socket_user
        # 房间
        self.room: RoomInterface = None
        # 是否房主
        self.master: bool = False
        # 是否准备
        self.ready: bool = False
        # 身份
        self.identity: str = "unknown"
        # 将领
        self.leader_id: int = -1

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
