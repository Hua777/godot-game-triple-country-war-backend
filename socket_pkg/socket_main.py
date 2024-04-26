import json
import uuid

from twisted.internet import protocol

from http_pkg.http_user import save_user_online_tag
from http_pkg.http_room import (
    create_room,
    create_room_user,
    set_room_role_count,
    set_room_master,
)

SPLIT_STR = "[SPLIT]"


class Room:
    def __init__(self, id):
        super().__init__()
        self.id = id
        self.user_sockets: list[TcbwSocketProtocol] = []

    def add_user(self, user_socket):
        self.user_sockets.append(user_socket)

    def remove_user(self, user_socket):
        self.user_sockets.remove(user_socket)

    def is_empty(self):
        return len(self.user_sockets) == 0

    def get_any_user(self):
        return self.user_sockets[0] if len(self.user_sockets) > 0 else None


room_map: dict[str, Room] = {}


class TcbwSocketProtocol(protocol.Protocol):
    def __init__(self, addr) -> None:
        super().__init__()
        self.addr = addr
        self.account: str = None
        self.room: Room = None

    def connectionMade(self):
        pass

    @staticmethod
    def gen_msg_id():
        msg_id = uuid.uuid4()
        return str(msg_id)

    def init_user(self):
        pass

    def create_room(self, id, name, password):
        create_room(
            id,
            self.account,
            name,
            password,
        )
        self.room = Room(id)
        room_map[self.room.id] = self.room
        self.room.add_user(self)

    def join_room(self):
        pass

    def leave_room(self):
        if self.room is not None:
            self.room.remove_user(self)
            if self.room.is_empty():
                # 房间没人了，删除房间
                del room_map[self.room.id]
            else:
                # 设置新房主
                new_master = self.room.get_any_user()
                set_room_master(self.room.id, new_master.account)
                for user_socket in self.room.user_sockets:
                    # 广播通知房间有人离开
                    user_socket.transport.write(
                        (
                            TcbwSocketProtocol.gen_msg_id()
                            + SPLIT_STR
                            + "user-leave"
                            + SPLIT_STR
                            + self.account
                        ).encode()
                    )
                    # 广播通知换房主
                    user_socket.transport.write(
                        (
                            TcbwSocketProtocol.gen_msg_id()
                            + SPLIT_STR
                            + "change-master-to"
                            + SPLIT_STR
                            + new_master.account
                        ).encode()
                    )
            self.room = None

    def exit_game(self):
        self.leave_room()
        if self.account is not None:
            save_user_online_tag(self.account, False)

    def dataReceived(self, data):
        try:
            data_decode = data.decode("utf-8")
            print("Received data:", data_decode)
            split_array = data_decode.split(SPLIT_STR)
            msg_id = split_array[0]
            command = split_array[1]
            value = split_array[2]
            if command == "online":
                self.account = value
                save_user_online_tag(self.account, self.addr.host, self.addr.port, True)
                self.init_user()
            elif command == "create-room":
                info = json.loads(value)
                self.create_room(info["id"], info["name"], info["password"])
            elif command == "join-room":
                self.join_room()
            elif command == "leave-room":
                self.leave_room()
            elif command == "ack":
                return
            self.transport.write(
                (msg_id + SPLIT_STR + "ack" + SPLIT_STR + "ok").encode()
            )
        except Exception as ex:
            print("data parse error", ex)

    def connectionLost(self, reason):
        self.exit_game()


class TcbwSocketFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return TcbwSocketProtocol(addr)
