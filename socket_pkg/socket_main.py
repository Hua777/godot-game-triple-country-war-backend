import json
import uuid

from autobahn.twisted.websocket import WebSocketServerProtocol

from http_pkg.http_user import save_user_online_tag, get_user
from http_pkg.http_room import (
    create_room,
    create_room_user,
    set_room_role_count,
    set_room_master,
    get_room,
    set_room_close,
)


def parse_msg(data: bytes) -> tuple[str, str, str, dict]:
    data_decode = data.decode("utf-8")
    print("[websocket] received message:", data_decode)
    value = json.loads(data_decode)
    return (value["msg_id"], value["mode"], value["command"], value)


class Room:
    def __init__(self, id):
        super().__init__()
        self.id = id
        self.user_sockets: list[TcbwSocketProtocol] = []
        self.ready_users: set[str] = set()

    def add_user(self, user_socket):
        self.user_sockets.append(user_socket)

    def remove_user(self, user_socket):
        self.user_sockets.remove(user_socket)

    def is_empty(self):
        return len(self.user_sockets) == 0

    def get_any_user(self):
        return self.user_sockets[0] if len(self.user_sockets) > 0 else None

    def user_ready_or_not(self, account):
        if account in self.ready_users:
            self.ready_users.remove(account)
        else:
            self.ready_users.add(account)

    def user_unready(self, account):
        self.ready_users.discard(account)


room_map: dict[str, Room] = {}


class TcbwSocketProtocol(WebSocketServerProtocol):
    def __init__(self) -> None:
        super().__init__()
        self.account: str = None
        self.room: Room = None

    def onConnect(self, request):
        self.host = request.host

    def onOpen(self):
        pass

    def onMessage(self, payload: bytes, isBinary):
        (msg_id, mode, command, info) = parse_msg(payload)
        if mode == "request":
            if command == "online":
                self.online_game(msg_id, info)
            elif command == "create-room":
                self.create_room(msg_id, info)
            elif command == "join-room":
                self.join_room(msg_id, info)
            elif command == "room-info":
                self.room_info(msg_id, info)
            elif command == "leave-room":
                self.leave_room(msg_id, info)
            elif command == "kick-out-user-from-room":
                self.kick_out_user_from_room(msg_id, info)
            elif command == "change-room-property":
                self.change_room_property(msg_id, info)
            elif command == "ready-or-not":
                self.ready_or_not(msg_id, info)
            elif command == "start-game":
                self.start_game(msg_id, info)

    def onClose(self, wasClean, code, reason):
        if self.account is not None:
            print(f"[websocket] {self.account} exit game, reason: {reason}")
            self.leave_room()
            save_user_online_tag(self.account, self.host, False)

    def send_ack(self, command: str, msg_id: str, info: dict):
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

    def online_game(self, msg_id: str, info: dict):
        self.account = info["account"]
        save_user_online_tag(self.account, self.host, True)
        self.send_ack(
            "online",
            msg_id,
            {
                "msg": "上线成功",
            },
        )

    def is_not_in_room(self, msg_id: str, command: str) -> bool:
        if self.room is None:
            return True
        else:
            if msg_id is not None:
                self.send_ack(
                    command,
                    msg_id,
                    {
                        "msg": "已经在房间里",
                    },
                )
            return False

    def is_in_room(self, msg_id: str, command: str) -> bool:
        if self.room is not None:
            return True
        else:
            if msg_id is not None:
                self.send_ack(
                    command,
                    msg_id,
                    {
                        "msg": "不在房间里",
                    },
                )
            return False

    def is_room_master(self, msg_id: str, command: str) -> bool:
        room_in_db = get_room(self.room.id)
        if room_in_db["master_account"] == self.account:
            return True
        else:
            if msg_id is not None:
                self.send_ack(
                    command,
                    msg_id,
                    {
                        "msg": "你不是房主",
                    },
                )
            return False

    def is_not_room_master(self, msg_id: str, command: str) -> bool:
        room_in_db = get_room(self.room.id)
        if room_in_db["master_account"] != self.account:
            return True
        else:
            if msg_id is not None:
                self.send_ack(
                    command,
                    msg_id,
                    {
                        "msg": "你是房主",
                    },
                )
            return False

    def room_exists(self, msg_id: str, command: str, room_id: str):
        if room_id in room_map:
            return True
        else:
            if msg_id is not None:
                self.send_ack(
                    command,
                    msg_id,
                    {
                        "msg": "房间不存在",
                    },
                )
            return False

    def create_room(self, msg_id: str, info: dict):
        try:
            if self.is_not_in_room(msg_id, "create-room"):
                # 数据库创建房间
                create_room(
                    info["room_id"],
                    self.account,
                    info["room_name"],
                    info["room_password"],
                )
                # 初始化自己的房间
                self.room = Room(info["room_id"])
                # 全局保存房间列表
                room_map[self.room.id] = self.room
                # 将自己丢进去房间
                self.room.add_user(self)
                # 回复
                self.send_ack(
                    "create-room",
                    msg_id,
                    {},
                )
        except Exception as ex:
            self.send_ack(
                "create-room",
                msg_id,
                {
                    "msg": "创建房间失败",
                },
            )

    def join_room(self, msg_id: str, info: dict):
        if self.is_not_in_room(msg_id, "join-room"):
            room_in_db = get_room(info["room_id"])
            # 比对房间密码
            if int(room_in_db["password"]) == int(info["input_room_password"]):
                # 密码正确，检查房间是否存在于内存
                if self.room_exists(msg_id, "join-room", info["room_id"]):
                    self.room = room_map[info["room_id"]]
                    for user_socket in self.room.user_sockets:
                        # 广播通知房间有人进来
                        user_socket.send_command(
                            "user-join",
                            {
                                "account": self.account,
                            },
                        )
                    # 把自己丢进去房间
                    self.room.add_user(self)
                    # 回复
                    if msg_id is not None:
                        self.send_ack(
                            "join-room",
                            msg_id,
                            {},
                        )
            else:
                # 密码错误
                if msg_id is not None:
                    self.send_ack(
                        "join-room",
                        msg_id,
                        {
                            "msg": "密码错误无法加入",
                        },
                    )

    def room_info(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "room-info"):
            response = {"room": get_room(self.room.id), "users": {}}
            for user_socket in self.room.user_sockets:
                user = get_user(user_socket.account)
                response["users"][user_socket.account] = user
                if user_socket.account in self.room.ready_users:
                    user["ready"] = True
                else:
                    user["ready"] = False
            if msg_id is not None:
                self.send_ack(
                    "room-info",
                    msg_id,
                    response,
                )

    def leave_room(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "leave-room"):
            self.room.remove_user(self)
            if self.room.is_empty():
                # 房间没人了，内存删除房间
                del room_map[self.room.id]
                # 去数据库把房间删掉
                set_room_close(self.room.id)
            else:
                room_in_db = get_room(self.room.id)
                if room_in_db["master_account"] == self.account:
                    # 如果离开的是房主，则找新房主
                    new_master = self.room.get_any_user()
                    # 新房主不能是已经准备的状态
                    self.room.user_unready(new_master.account)
                    # 数据库设置新房主
                    set_room_master(self.room.id, new_master.account)
                for user_socket in self.room.user_sockets:
                    # 广播通知房间有人离开
                    user_socket.send_command(
                        "user-leave",
                        {
                            "account": self.account,
                        },
                    )
            # 将自己的房间设置为空
            self.room = None
            # 回复
            if msg_id is not None:
                self.send_ack(
                    "leave-room",
                    msg_id,
                    {},
                )

    def kick_out_user_from_room(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "kick-out-user-from-room"):
            if self.is_room_master(msg_id, "kick-out-user-from-room"):
                # 不能踢掉自己
                if self.account != info["account"]:
                    # 找到被踢掉的人的 socket
                    target_user_socket = None
                    for user_socket in self.room.user_sockets:
                        if user_socket.account == info["account"]:
                            target_user_socket = user_socket
                            break
                    if target_user_socket is not None:
                        # 将这个人从内存移除
                        self.room.remove_user(target_user_socket)
                        # 将这个人的房间置为空
                        target_user_socket.room = None
                        for user_socket in self.room.user_sockets:
                            # 广播通知房间有人离开
                            user_socket.send_command(
                                "user-leave",
                                {
                                    "account": target_user_socket.account,
                                },
                            )
                        # 通知这个人离开房间
                        target_user_socket.send_command(
                            "kick-out",
                            {},
                        )
                    # 回复
                    if msg_id is not None:
                        self.send_ack(
                            "kick-out-user-from-room",
                            msg_id,
                            {},
                        )
                else:
                    if msg_id is not None:
                        self.send_ack(
                            "kick-out-user-from-room",
                            msg_id,
                            {
                                "msg": "不能将自己踢出房间",
                            },
                        )

    def change_room_property(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "change-room-property"):
            if self.is_room_master(msg_id, "change-room-property"):
                # 数据库更新房间属性
                set_room_role_count(
                    self.room.id,
                    info["loyal_count"],
                    info["traitor_count"],
                    info["rebel_count"],
                )
                for user_socket in self.room.user_sockets:
                    # 通知所有人房间属性变更了
                    user_socket.send_command(
                        "room-property-changed",
                        {},
                    )
                # 回复
                if msg_id is not None:
                    self.send_ack(
                        "change-room-property",
                        msg_id,
                        {},
                    )

    def ready_or_not(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "ready-or-not"):
            if self.is_not_room_master(msg_id, "ready-or-not"):
                self.room.user_ready_or_not(self.account)
                for user_socket in self.room.user_sockets:
                    # 通知所有人有人准备
                    user_socket.send_command(
                        "user-ready-changed",
                        {},
                    )
                if msg_id is not None:
                    self.send_ack(
                        "ready-or-not",
                        msg_id,
                        {},
                    )

    def start_game(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "start-game"):
            if self.is_room_master(msg_id, "start-game"):
                for user_socket in self.room.user_sockets:
                    # 通知所有人开始游戏
                    user_socket.send_command(
                        "game-started",
                        {},
                    )
                if msg_id is not None:
                    self.send_ack(
                        "start-game",
                        msg_id,
                        {},
                    )
