from game.socket_user_for_room_interface import SocketUserForRoomInterface
from game.leader.leader_pool import leader_pool

import random


from http_pkg.http_game import (
    random_leaders,
    random_cards,
    create_game_operate_history_for_turn_changed,
)


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
                    leader_pool[user.leader["id"]].after_your_turn(user)
                else:
                    leader_pool[user.leader["id"]].after_other_turn(
                        user, self.turn_user()
                    )
        self.turn_index += 1
        self.turn_index = self.turn_index % len(self.users)
        create_game_operate_history_for_turn_changed(
            self.game_id, self.turn_user().socket_user.account
        )
        for user in self.users:
            if user == self.turn_user():
                leader_pool[user.leader["id"]].before_your_turn(user)
            else:
                leader_pool[user.leader["id"]].before_other_turn(user, self.turn_user())

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
                        leader_pool[user.leader["id"]].after_your_turn(user)
                    else:
                        leader_pool[user.leader["id"]].after_other_turn(
                            user, self.turn_user()
                        )
            self.turn_index = index
            create_game_operate_history_for_turn_changed(
                self.game_id, self.turn_user().socket_user.account
            )
            for user in self.users:
                if user == self.turn_user():
                    leader_pool[user.leader["id"]].before_your_turn(user)
                else:
                    leader_pool[user.leader["id"]].before_other_turn(
                        user, self.turn_user()
                    )

    def turn_user(self) -> SocketUserForRoomInterface:
        return self.users[self.turn_index]

    def random_suit_and_rank(self) -> tuple[str, int]:
        suit = random.choice(["spades", "hearts", "clubs", "diamonds"])
        rank = random.randint(1, 13)
        return suit, rank
