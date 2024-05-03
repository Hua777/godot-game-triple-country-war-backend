from http_pkg.http_game import get_card


# 扑克牌
class CardInterface:
    # 花色、大小
    # 花色种类：黑桃(spades)、红桃(hearts)、梅花(clubs)、方块(diamonds)
    def __init__(self, id: int) -> None:
        self.id: int = id
        self.card = get_card(id)
        self.suit: str = "unknown"
        self.rank: int = 0

    # 距离，武器时代表可攻击距离，马匹时代表被看的距离调整
    def distance(self) -> int:
        return 0
