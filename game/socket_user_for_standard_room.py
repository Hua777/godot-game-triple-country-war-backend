from socket_pkg.socket_user import SocketUser
from game.room_interface import RoomInterface
from game.socket_user_for_room_interface import SocketUserForRoomInterface

from http_pkg.http_user import save_user_online_tag, get_user
from http_pkg.http_room import (
    create_room,
    create_room_user,
    set_room_role_count,
    set_room_master,
    get_room,
    set_room_close,
)


class StandardRoom(RoomInterface):
    def __init__(self, id: str):
        super().__init__(id)


standard_rooms: dict[str, StandardRoom] = {}


class SocketUserForStandardRoom(SocketUserForRoomInterface):
    def __init__(self, socket_user: SocketUser) -> None:
        super().__init__(socket_user)
        self.room: StandardRoom = None

    def on_request(self, msg_id: str, command: str, info: dict):
        if command == "create-room":
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

    def on_close(self):
        return super().on_close()

    def is_not_in_room(self, msg_id: str, command: str) -> bool:
        if self.room is None:
            return True
        else:
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
        if room_in_db["master_account"] == self.socket_user.account:
            return True
        else:
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
            self.send_ack(
                command,
                msg_id,
                {
                    "msg": "你是房主",
                },
            )
            return False

    def room_exists(self, msg_id: str, command: str, room_id: str):
        if room_id in standard_rooms:
            return True
        else:
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
                    self.socket_user.account,
                    info["room_name"],
                    info["room_password"],
                )
                # 初始化自己的房间
                self.room = StandardRoom(info["room_id"])
                # 全局保存房间列表
                standard_rooms[self.room.id] = self.room
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
                    self.room = standard_rooms[info["room_id"]]
                    # 把自己丢进去房间
                    self.room.add_user(self)
                    # 广播通知房间有人进来
                    self.room.broadcast(
                        "user-join",
                        {
                            "account": self.socket_user.account,
                        },
                    )
                    # 回复
                    self.send_ack(
                        "join-room",
                        msg_id,
                        {},
                    )
            else:
                # 密码错误
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
            for socket_user_for_standard_room in self.room.users:
                user = get_user(socket_user_for_standard_room.socket_user.account)
                response["users"][
                    socket_user_for_standard_room.socket_user.account
                ] = user
                user["ready"] = socket_user_for_standard_room.ready
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
                del standard_rooms[self.room.id]
                # 去数据库把房间删掉
                set_room_close(self.room.id)
            else:
                room_in_db = get_room(self.room.id)
                if room_in_db["master_account"] == self.socket_user.account:
                    # 如果离开的是房主，则找新房主
                    new_master = self.room.get_any_user()
                    # 新房主不能是已经准备的状态
                    self.room.user_unready(new_master.socket_user.account)
                    # 数据库设置新房主
                    set_room_master(self.room.id, new_master.socket_user.account)
                # 广播通知房间有人离开
                self.room.broadcast(
                    "user-leave",
                    {
                        "account": self.socket_user.account,
                    },
                )
            # 将自己的房间设置为空
            self.room = None
            # 设置为未准备
            self.ready = False
            # 回复
            self.send_ack(
                "leave-room",
                msg_id,
                {},
            )

    def kick_out_user_from_room(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "kick-out-user-from-room"):
            if self.is_room_master(msg_id, "kick-out-user-from-room"):
                # 不能踢掉自己
                if self.socket_user.account != info["account"]:
                    # 找到被踢掉的人的 socket
                    target_user_socket: SocketUserForStandardRoom = self.room.get_user(
                        info["account"]
                    )
                    if target_user_socket is not None:
                        # 将这个人从内存移除
                        self.room.remove_user(target_user_socket)
                        # 将这个人的房间置为空
                        target_user_socket.room = None
                        # 广播通知房间有人离开
                        self.room.broadcast(
                            "user-leave",
                            {
                                "account": target_user_socket.socket_user.account,
                            },
                        )
                        # 通知这个人离开房间
                        target_user_socket.send_command(
                            "kick-out",
                            {},
                        )
                    # 回复
                    self.send_ack(
                        "kick-out-user-from-room",
                        msg_id,
                        {},
                    )
                else:
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
                # 通知所有人房间属性变更了
                self.room.broadcast(
                    "room-property-changed",
                    {
                        "loyal_count": info["loyal_count"],
                        "traitor_count": info["traitor_count"],
                        "rebel_count": info["rebel_count"],
                    },
                )
                # 回复
                self.send_ack(
                    "change-room-property",
                    msg_id,
                    {},
                )

    def ready_or_not(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "ready-or-not"):
            if self.is_not_room_master(msg_id, "ready-or-not"):
                # 变更自己的准备状态
                self.room.user_ready_or_not(self.socket_user.account)
                # 通知所有人有人准备
                self.room.broadcast(
                    "user-ready-changed",
                    {
                        "account": self.socket_user.account,
                    },
                )
                # 回复
                self.send_ack(
                    "ready-or-not",
                    msg_id,
                    {},
                )

    def start_game(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "start-game"):
            if self.is_room_master(msg_id, "start-game"):
                # 通知所有人开始游戏
                self.room.broadcast("game-started", {})
                # 回复
                self.send_ack(
                    "start-game",
                    msg_id,
                    {},
                )
