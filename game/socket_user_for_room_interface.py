from socket_pkg.socket_user import SocketUser

from game.room_interface import RoomInterface
from game.leader.leader_pool import leader_pool
from game.card.card_pool import card_pool


class SocketUserForRoomInterface:
    def __init__(self, socket_user: SocketUser) -> None:
        # Socket
        self.socket_user = socket_user
        # 重置
        self.reset_room()
        self.reset_game()

    def reset_room(self):
        # 房间
        self.room: RoomInterface = None
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

    def select_leader(self, leader):
        self.leader = leader
        leader_pool[self.leader["id"]].when_prepare(self)

    # 你攻击别人的距离
    def get_attack_distance(self) -> int:
        attackable_range = 1
        if self.weapon is not None:
            attackable_range = card_pool[self.weapon["id"]].distance()
        return attackable_range

    # 你的距离位移
    def get_distance_adjust(self) -> int:
        attacked_range = 0
        if self.horse is not None:
            attacked_range = card_pool[self.horse["id"]].distance()
        return attacked_range
