from game.socket_user_for_room_interface import SocketUserForRoomInterface

import random


from http_pkg.http_game import random_leaders


class RoomInterface:
    def __init__(self, id: str) -> None:
        # 房间号
        self.id = id
        # 房间用户
        self.users: list[SocketUserForRoomInterface] = []
        # 游戏ID
        self.game_id: int = None
        # 忠臣数量
        self.loyal_count: int = 0
        # 内奸数量
        self.traitor_count: int = 0
        # 反贼数量
        self.rebel_count: int = 0
        # 身份卡片
        self.identity_cards: list[dict] = []
        # 将领卡片池
        self.leader_pool: list[dict] = []

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
        self.leader_pool = random_leaders(len(self.users) * 5)
        random.shuffle(self.leader_pool)
