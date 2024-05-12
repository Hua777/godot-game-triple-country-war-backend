import random

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
    random_leaders,
    random_cards,
    create_game_operate_history_for_turn_changed,
)


class Room:
    def __init__(self, id: str) -> None:
        # 房间号
        self.id = id
        # 房间用户
        self.users: list[SocketUserForStandardRoom] = []
        # 游戏ID
        self.game_id: int = None
        # 忠臣数量
        self.loyal_count: int = 0
        # 内奸数量
        self.traitor_count: int = 0
        # 反贼数量
        self.rebel_count: int = 0
        # 主公可选择将领数量
        self.master_leader_selected_count: int = 5
        # 其他人可选择将领数量
        self.other_leader_selected_count: int = 3
        # 首次分卡数量
        self.first_get_card_count: int = 5
        # 每次发卡数量
        self.every_get_card_count: int = 2
        # 初始化游戏
        self.reset_game()

    def reset_game(self):
        # 身份卡片
        self.identity_cards: list[dict] = []
        # 主公将领卡片池
        self.master_leader_pool: list[dict] = []
        # 其他人将领卡片池
        self.other_leader_pool: list[dict] = []
        # 谁的回合
        self.turn_index = -1

    def add_user(self, user):
        self.users.append(user)

    def remove_user(self, user):
        self.users.remove(user)

    def is_empty(self) -> bool:
        return len(self.users) == 0

    def get_any_user(self):
        return self.users[0] if len(self.users) > 0 else None

    def user_ready_or_not(self, account: str):
        for user in self.users:
            if user.socket_user.account == account:
                user.ready = not user.ready

    def user_unready(self, account: str):
        for user in self.users:
            if user.socket_user.account == account:
                user.ready = False

    def broadcast(self, command: str, info: dict):
        for user in self.users:
            user.send_command(command, info)

    def get_user(self, account: str):
        for user in self.users:
            if user.socket_user.account == account:
                return user
        return None

    def all_user_ready(self) -> bool:
        for user in self.users:
            if not user.master and not user.ready:
                return False
        return True

    def generate_identity_cards(self):
        self.identity_cards = []
        self.identity_cards.append(
            {
                "identity": "master",
                "selected": False,
            }
        )
        for i in range(self.loyal_count):
            self.identity_cards.append(
                {
                    "identity": "loyal",
                    "selected": False,
                }
            )
        for i in range(self.traitor_count):
            self.identity_cards.append(
                {
                    "identity": "traitor",
                    "selected": False,
                }
            )
        for i in range(self.rebel_count):
            self.identity_cards.append(
                {
                    "identity": "rebel",
                    "selected": False,
                }
            )
        # shuffle array
        random.shuffle(self.identity_cards)

    def generate_leader_pool(self):
        self.master_leader_pool = random_leaders(self.master_leader_selected_count)
        self.other_leader_pool = random_leaders(
            self.other_leader_selected_count * len(self.users)
        )

    def draw_cards(self, count) -> list[dict]:
        return random_cards(count)

    def get_user_index(self, user) -> int:
        return self.users.index(user)

    def next_turn(self):
        if self.turn_index != -1:
            for user in self.users:
                if user == self.turn_user():
                    pass
                    # leader_pool[user.leader["id"]].after_your_turn(user)
                else:
                    pass
                    # leader_pool[user.leader["id"]].after_other_turn(
                    #     user, self.turn_user()
                    # )
        self.turn_index += 1
        self.turn_index = self.turn_index % len(self.users)
        create_game_operate_history_for_turn_changed(
            self.game_id, self.turn_user().socket_user.account
        )
        for user in self.users:
            if user == self.turn_user():
                pass
                # leader_pool[user.leader["id"]].before_your_turn(user)
            else:
                pass
                # leader_pool[user.leader["id"]].before_other_turn(user, self.turn_user())

    def set_turn(self, account: str):
        index = -1
        for i, user in enumerate(self.users):
            if user.account == account:
                index = i
                break
        if index >= 0:
            if self.turn_index != -1:
                for user in self.users:
                    if user == self.turn_user():
                        pass
                        # leader_pool[user.leader["id"]].after_your_turn(user)
                    else:
                        pass
                        # leader_pool[user.leader["id"]].after_other_turn(
                        #     user, self.turn_user()
                        # )
            self.turn_index = index
            create_game_operate_history_for_turn_changed(
                self.game_id, self.turn_user().socket_user.account
            )
            for user in self.users:
                if user == self.turn_user():
                    pass
                    # leader_pool[user.leader["id"]].before_your_turn(user)
                else:
                    pass
                    # leader_pool[user.leader["id"]].before_other_turn(
                    #     user, self.turn_user()
                    # )

    def turn_user(self):
        return self.users[self.turn_index]

    def random_suit_and_rank(self) -> tuple[str, int]:
        suit = random.choice(["spades", "hearts", "clubs", "diamonds"])
        rank = random.randint(1, 13)
        return suit, rank


standard_rooms: dict[str, Room] = {}


class SocketUserForStandardRoom:
    def __init__(self, socket_user) -> None:
        # Socket User
        self.socket_user = socket_user
        # 重置
        self.reset_room()
        self.reset_game()

    def reset_room(self):
        # 房间
        self.room = None
        # 是否房主
        self.master: bool = False
        # 是否准备
        self.ready: bool = False

    def reset_game(self):
        # 身份
        self.identity: str = "unknown"
        # 将领
        self.leader: dict = None
        # 生命值
        self.life: int = 0
        # 武器
        self.weapon: dict = None
        # 装备
        self.equipment: dict = None
        # 马匹
        self.horse: dict = None
        # 附加状态列表
        self.status_list: list[dict] = []
        # 手上拿的卡
        self.hand_cards: list[dict] = []

    def send_ack(self, command: str, msg_id: str, info: dict):
        self.socket_user.send_ack(command, msg_id, info)

    def send_command(self, command: str, info: dict):
        self.socket_user.send_command(command, info)

    def select_leader(self, leader):
        self.leader = leader
        # leader_pool[self.leader["id"]].when_prepare(self)

    # 你攻击别人的距离
    def get_attack_distance(self) -> int:
        attackable_range = 1
        if self.weapon is not None:
            pass
            # attackable_range = card_pool[self.weapon["id"]].distance()
        return attackable_range

    # 你的距离位移
    def get_distance_adjust(self) -> int:
        attacked_range = 0
        if self.horse is not None:
            pass
            # attacked_range = card_pool[self.horse["id"]].distance()
        return attacked_range

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
        elif command == "game-info":
            self.game_info(msg_id, info)
        elif command == "first-draw-cards":
            self.first_draw_cards(msg_id, info)
        elif command == "draw-cards":
            self.draw_cards(msg_id, info)

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

    def is_your_turn(self, msg_id: str, command: str) -> bool:
        if self == self.room.turn_user():
            return True
        else:
            self.send_ack(
                command,
                msg_id,
                {
                    "msg": "还不是你的回合",
                },
            )

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
                self.room = Room(info["room_id"])
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
            # 房间踢出自己
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
            # 设置为未准备
            # 设置非房主
            self.reset_room()
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
                # 更新房间属性
                self.room.loyal_count = int(info["loyal_count"])
                self.room.traitor_count = int(info["traitor_count"])
                self.room.rebel_count = int(info["rebel_count"])
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
                    self.room.loyal_count
                    + self.room.traitor_count
                    + self.room.rebel_count
                    + 1
                ) == len(self.room.users):
                    # 检查是否都准备好了
                    if self.room.is_all_ready():
                        # 重置房间游戏状态
                        self.room.reset_game()
                        # 创建游戏
                        game_id = create_game(
                            self.room.id,
                            self.room.loyal_count,
                            self.room.traitor_count,
                            self.room.rebel_count,
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
                if self.master:
                    # 回复
                    self.send_ack(
                        "list-leader-cards",
                        msg_id,
                        {
                            "leader_cards": self.room.master_leader_pool,
                        },
                    )
                else:
                    # index of user
                    index = self.room.users.index(self.socket_user)
                    # 回复
                    self.send_ack(
                        "list-leader-cards",
                        msg_id,
                        {
                            "leader_cards": self.room.other_leader_pool[
                                index
                                * self.room.other_leader_selected_count : index
                                * (self.room.other_leader_selected_count + 1)
                            ],
                        },
                    )

    # 大家都选完身份了
    def after_all_choose_identity(self):
        for user in self.room.users:
            if user.identity == "unknown":
                return
        self.room.broadcast("choose-identity-finished", {})

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
                            identity_card["identity"],
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
                        # 检查大家是否选完身份
                        self.after_all_choose_identity()
                else:
                    self.send_ack(
                        "choose-identity",
                        msg_id,
                        {
                            "msg": "你已经选择过身份了",
                        },
                    )

    # 大家都选完将领了
    def all_choose_leader(self):
        for user in self.room.users:
            if user.leader is None:
                return
        for user in self.room.users:
            pass
            # leader_pool[user.leader["id"]].after_everybody_prepare()
        self.room.broadcast("choose-leader-finished", {})

    # 选择将领
    def choose_leadaer(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "choose-leader"):
            if self.is_in_game(msg_id, "choose-leader"):
                if self.leader is None:
                    # 更新用户将领
                    self.select_leader(info["leader"])
                    update_game_user_leader_id(
                        self.room.game_id, self.socket_user.account, self.leader["id"]
                    )
                    # 回复
                    self.send_ack(
                        "choose-leader",
                        msg_id,
                        {},
                    )
                    # 检查大家是否选完将领
                    self.all_choose_leader()
                else:
                    self.send_ack(
                        "choose-leader",
                        msg_id,
                        {
                            "msg": "你已经选择过将领了",
                        },
                    )

    def calculate_distance(self, a, b):
        d = abs(b - a)
        d_circular = (len(self.room.users) - b + a) % len(self.room.users)
        return min(d, d_circular)

    # 游戏信息
    def game_info(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "game-info"):
            if self.is_in_game(msg_id, "game-info"):
                # 我的位置
                my_index = self.room.get_user_index(self)
                # 回复
                self.send_ack(
                    "game-info",
                    msg_id,
                    {
                        "hand_cards": self.hand_cards,
                        "users": [
                            {
                                "account": user.socket_user.account,
                                "leader": user.leader,
                                "life": user.life,
                                "hand_card_count": len(user.hand_cards),
                                "weapon": user.weapon,
                                "equipment": user.equipment,
                                "horse": user.horse,
                                "status_list": user.status_list,
                                "attack_distance": user.get_attack_distance(),
                                "distance_adjust": user.get_distance_adjust(),
                                "you_to_user_distance": (
                                    0
                                    if index == my_index
                                    else self.calculate_distance(my_index, index)
                                    + user.get_distance_adjust()
                                ),
                                "user_to_you_distance": (
                                    0
                                    if index == my_index
                                    else self.calculate_distance(my_index, index)
                                    + self.get_distance_adjust()
                                ),
                            }
                            for (index, user) in enumerate(self.room.users)
                        ],
                    },
                )

    # 检查大家是否都完成了第一次抽卡
    def all_first_draw_cards(self):
        for user in self.room.users:
            if len(user.hand_cards) != self.room.first_get_card_count:
                return
        self.room.broadcast("first-draw-cards-finished", {})
        # 开始第一回合
        self.room.next_turn()

    # 游戏刚开始的抽卡
    def first_draw_cards(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "first-draw-cards"):
            if self.is_in_game(msg_id, "first-draw-cards"):
                # 检查是否抽过卡
                if len(self.hand_cards) != self.room.first_get_card_count:
                    # 抽卡
                    for card in self.room.draw_cards(self.room.first_get_card_count):
                        self.hand_cards.append(card)
                    # 回复
                    self.send_ack(
                        "first-draw-cards",
                        msg_id,
                        {
                            "hand_cards": self.hand_cards,
                        },
                    )
                    # 检查大家是否都完成了第一次抽卡
                    self.all_first_draw_cards()
                else:
                    self.send_ack(
                        "first-draw-cards",
                        msg_id,
                        {
                            "msg": "你已经抽过卡了",
                        },
                    )

    # 抽卡
    def draw_cards(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "draw-cards"):
            if self.is_in_game(msg_id, "draw-cards"):
                if self.is_your_turn(msg_id, "draw-cards"):
                    # 抽卡前
                    # leader_pool[self.leader["id"]].before_you_draw_card(self)
                    # 抽卡
                    draw_cards = self.room.draw_cards(self.room.every_get_card_count)
                    for card in draw_cards:
                        self.hand_cards.append(card)
                    # 抽卡后
                    # leader_pool[self.leader["id"]].after_you_draw_card(self)
                    # 回复
                    self.send_ack(
                        "draw-cards",
                        msg_id,
                        {
                            "draw_cards": draw_cards,
                            "hand_cards": self.hand_cards,
                        },
                    )

    # 结束我的回合
    def finish_my_turn(self, msg_id: str = None, info: dict = {}):
        if self.is_in_room(msg_id, "finish-my-turn"):
            if self.is_in_game(msg_id, "finish-my-turn"):
                if self.is_your_turn(msg_id, "finish-my-turn"):
                    self.room.next_turn()
                    # 广播轮到谁了
                    self.room.broadcast(
                        "turn-changed",
                        {
                            "account": self.room.turn_user().socket_user.account,
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
    #                 user.reset_game()
    #                 user.ready = False
