from socket_pkg.socket_user import SocketUser
from game.room_interface import RoomInterface
from game.socket_user_for_room_interface import SocketUserForRoomInterface

from http_pkg.http_user import get_user
from http_pkg.http_room import (
    create_room,
    set_room_role_count,
    set_room_master,
    get_room,
    set_room_close,
)
from http_pkg.http_game import (
    create_game,
    finish_game,
    create_game_user,
    update_game_user_identity,
    update_game_user_leader_id,
    create_game_operate_history,
    get_game_user,
)


class StandardRoom(RoomInterface):
    def __init__(self, id: str):
        super().__init__(id)


standard_rooms: dict[str, StandardRoom] = {}


class SocketUserForStandardRoom(SocketUserForRoomInterface):
    def __init__(self, socket_user: SocketUser) -> None:
        super().__init__(socket_user)

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
        elif command == "list-identity":
            self.list_identity(msg_id, info)
        elif command == "list-leaders":
            self.list_leaders(msg_id, info)
        elif command == "choose-identity":
            self.choose_identity(msg_id, info)
        elif command == "choose-leader":
            self.choose_leader(msg_id, info)

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
        if self.master:
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
        if not self.master:
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

    def is_in_game(self, msg_id: str, command: str) -> bool:
        if self.room.game_id is not None:
            return True
        else:
            self.send_ack(
                command,
                msg_id,
                {
                    "msg": "游戏未开始",
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
                # 内存设置房主
                self.master = True
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
                if self.master:
                    # 如果离开的是房主，则找新房主
                    new_master = self.room.get_any_user()
                    # 新房主不能是已经准备的状态
                    self.room.user_unready(new_master.socket_user.account)
                    # 数据库设置新房主
                    set_room_master(self.room.id, new_master.socket_user.account)
                    # 内存设置房主
                    new_master.master = True
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
            # 设置非房主
            self.master = False
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
                # 检查身份数量加总是否等于房间游戏人数数量
                if (
                    info["loyal_count"]
                    + info["traitor_count"]
                    + info["rebel_count"]
                    + 1
                ) == len(self.room.users):
                    # 检查是否都准备好了
                    if self.room.is_all_ready():
                        # 创建游戏
                        game_id = create_game(
                            self.room.id,
                            info["loyal_count"],
                            info["traitor_count"],
                            info["rebel_count"],
                        )
                        # 创建游戏用户
                        for user in self.room.users:
                            user.room.game_id = game_id
                            create_game_user(game_id, user.socket_user.account)
                        # 随机创建身份
                        self.room.generate_identity_cards()
                        # 随机创建将领
                        self.room.generate_leader_pool()
                        # 通知所有人开始游戏
                        self.room.broadcast(
                            "game-started",
                            {
                                "game_id": game_id,
                            },
                        )
                        # 回复
                        self.send_ack(
                            "start-game",
                            msg_id,
                            {
                                "game_id": game_id,
                            },
                        )
                    else:
                        self.send_ack(
                            "start-game",
                            msg_id,
                            {
                                "msg": "房间内玩家未全部准备",
                            },
                        )
                else:
                    self.send_ack(
                        "start-game",
                        msg_id,
                        {
                            "msg": "身份数量与游戏人数不匹配",
                        },
                    )

    # 列出当前游戏的身份
    def list_identity_cards(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "list-identity-cards"):
            if self.is_in_game(msg_id, "list-identity-cards"):
                # 回复
                self.send_ack(
                    "list-identity-cards",
                    msg_id,
                    {
                        "identity_cards": map(
                            lambda x: x["selected"], self.room.identity_cards
                        ),
                    },
                )

    # 列出当前用户对应的游戏将领
    def list_leader_cards(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "list-leader-cards"):
            if self.is_in_game(msg_id, "list-leader-cards"):
                # index of user
                index = self.room.users.index(self.socket_user)
                # 回复
                self.send_ack(
                    "list-leader-cards",
                    msg_id,
                    {
                        "leader_cards": self.room.leader_pool[index * 5 : index * 6],
                    },
                )

    # 选择身份
    def choose_identity(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "choose-identity"):
            if self.is_in_game(msg_id, "choose-identity"):
                if self.identity == "unknown":
                    # TODO redis
                    identity_card = self.room.identity_cards[info["index"]]
                    if identity_card["selected"]:
                        # 已被选择
                        self.send_ack(
                            "choose-identity",
                            msg_id,
                            {
                                "msg": "该身份已被选择",
                            },
                        )
                    else:
                        identity_card["selected"] = True
                        # 更新用户身份
                        self.identity = identity_card["identity"]
                        update_game_user_identity(
                            self.room.game_id,
                            self.socket_user.account,
                            info["identity"],
                        )
                        # 广播通知有人选中了身份
                        self.room.broadcast(
                            "identity-changed",
                            {
                                "account": self.socket_user.account,
                            },
                        )
                        # 回复
                        self.send_ack(
                            "choose-identity",
                            msg_id,
                            {
                                "identity": identity_card["identity"],
                            },
                        )
                else:
                    self.send_ack(
                        "choose-identity",
                        msg_id,
                        {
                            "msg": "你已经选择过身份了",
                        },
                    )

    # 选择将领
    def choose_leadaer(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "choose-leader"):
            if self.is_in_game(msg_id, "choose-leader"):
                if self.leader_id == -1:
                    # 更新用户将领
                    self.leader_id = int(info["leader_id"])
                    update_game_user_leader_id(
                        self.room.game_id, self.socket_user.account, info["leader_id"]
                    )
                    # 回复
                    self.send_ack(
                        "choose-leader",
                        msg_id,
                        {},
                    )
                else:
                    self.send_ack(
                        "choose-leader",
                        msg_id,
                        {
                            "msg": "你已经选择过将领了",
                        },
                    )

    # def finish_game(self, msg_id: str = None, info: dict = {}):
    #     if self.is_in_room(msg_id, "finish-game"):
    #         if self.is_in_game(msg_id, "finish-game"):
    #             finish_game(
    #                 self.room.game_id, info["win_type"], info["winner_identity"]
    #             )
    #             # 清空所有玩家的身份、将领、游戏ID
    #             for user in self.room.users:
    #                 user.ready = False
    #                 user.room.game_id = None
    #                 user.identity = "unknown"
    #                 user.leader_id = -1
