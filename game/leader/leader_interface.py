from game.socket_user_for_room_interface import SocketUserForRoomInterface

from http_pkg.http_game import get_leader

"""
游戏开始 -> 游戏准备 -> 玩家回合开始 -> 玩家抽卡 -> 玩家出牌 -> 玩家弃牌 -> 玩家回合结束 -> 游戏结束
"""


# 将领技能详细实现
class LeaderInterface:
    def __init__(self, id: int) -> None:
        self.id: int = id
        self.leader: dict = get_leader(id)

    # 战斗前准备
    def when_prepare(self, user: SocketUserForRoomInterface):
        user.life = int(self.leader["life"])

    # 大家都准备好了
    def after_everybody_prepare(self, user: SocketUserForRoomInterface):
        pass

    # 你的回合开始
    def before_your_turn(self, user: SocketUserForRoomInterface):
        pass

    # 你的回合结束
    def after_your_turn(self, user: SocketUserForRoomInterface):
        pass

    # 别人的回合开始
    def before_other_turn(
        self, you: SocketUserForRoomInterface, other: SocketUserForRoomInterface
    ):
        pass

    # 别人的回合结束
    def after_other_turn(
        self, you: SocketUserForRoomInterface, other: SocketUserForRoomInterface
    ):
        pass

    # 抽卡前
    def before_you_draw_card(self, user: SocketUserForRoomInterface):
        pass

    # 抽卡后
    def after_you_draw_card(self, user: SocketUserForRoomInterface):
        pass
