from http_pkg.http_game import get_card


# 扑克牌
class CardInterface:
    def __init__(self, id: int) -> None:
        self.id: int = id
        self.card = get_card(id)

    # 距离，武器时代表可攻击距离，马匹时，代表被看的距离调整
    def distance(self) -> int:
        return 0
