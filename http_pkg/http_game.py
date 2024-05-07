from twisted.web import resource, server
import json

import http_tool
from mysql_tool import MYSQL_TOOL


def create_game(
    room_id: str, royal_count: int, traitor_count: int, rebel_count: int
) -> int:
    return MYSQL_TOOL.execute_update(
        f"insert into tcwb_game (room_id, royal_count, traitor_count, rebel_count) values ('{room_id}', {royal_count}, {traitor_count}, {rebel_count})"
    )


def finish_game(id: int, win_type: int, winner_identity: str):
    MYSQL_TOOL.execute_update(
        f"update tcwb_game set status = 1, win_type = {win_type}, winner_identity = '{winner_identity}', stop_time = CURRENT_TIMESTAMP where id = {id}"
    )
    MYSQL_TOOL.execute_update(
        f"update tcwb_game_user set status = 1 where game_id = {id}"
    )


def create_game_user(game_id: int, user_account: str):
    MYSQL_TOOL.execute_update(
        f"insert into tcwb_game_user (game_id, user_account) values ({game_id}, '{user_account}')"
    )


def update_game_user_identity(game_id: int, user_account: str, identity: str):
    MYSQL_TOOL.execute_update(
        f"update tcwb_game_user set identity = '{identity}' where game_id = {game_id} and user_account = '{user_account}'"
    )


def update_game_user_leader_id(game_id: int, user_account: str, leader_id: int):
    MYSQL_TOOL.execute_update(
        f"update tcwb_game_user set leader_id = {leader_id} where game_id = {game_id} and user_account = '{user_account}'"
    )


def create_game_operate_history(
    game_id: int, user_account: str, operate: str, detail: dict | list, describe: str
):
    MYSQL_TOOL.execute_update(
        f"insert into tcwb_game_operate_history (game_id, user_account, operate, detail, describe) values ({game_id}, '{user_account}', '{operate}', '{json.dumps(detail)}', '{describe}')"
    )


def create_game_operate_history_for_select_identity(
    game_id: int, user_account: str, identity: str
):
    create_game_operate_history(
        game_id, user_account, "select_identity", {"identity": identity}, "选择身份"
    )


def create_game_operate_history_for_select_leader(
    game_id: int, user_account: str, leader: dict
):
    create_game_operate_history(
        game_id, user_account, "select_leader", leader, "选择将领"
    )


def create_game_operate_history_for_draw_cards(
    game_id: int, user_account: str, cards: list
):
    create_game_operate_history(game_id, user_account, "draw_cards", cards, "摸牌")


def create_game_operate_history_for_use_card(
    game_id: int, user_account: str, card: dict, skill: dict, users: list[str]
):
    create_game_operate_history(
        game_id,
        user_account,
        "use_card",
        {
            "card": card,
            "skill": skill,
            "user_accounts": users,
        },
        "使用卡牌",
    )


def create_game_operate_history_for_remove_cards(
    game_id: int, user_account: str, cards: list
):
    create_game_operate_history(
        game_id,
        user_account,
        "remove_cards",
        cards,
        "移除卡牌",
    )


def create_game_operate_history_for_turn_changed(game_id: int, user_account: str):
    create_game_operate_history(game_id, user_account, "turn_changed", {}, "回合切换")


def get_game_user(game_id: int, user_account: str):
    return MYSQL_TOOL.execute_query_one(
        f"select * from tcwb_game_user where game_id = {game_id} and user_account = '{user_account}'"
    )


def random_leaders(count: int) -> list[dict]:
    return MYSQL_TOOL.execute_query(
        f"select * from tcwb_leader order by rand() limit {count}"
    )


def get_leader(id: int) -> dict:
    return MYSQL_TOOL.execute_query_one(f"select * from tcwb_leader where id = {id}")


def random_cards(count: int) -> list[dict]:
    return MYSQL_TOOL.execute_query(
        f"select * from tcwb_card order by rand() limit {count}"
    )


def get_card(id: int) -> dict:
    return MYSQL_TOOL.execute_query_one(f"select * from tcwb_card where id = {id}")


class HttpListIdentityResource(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)


class HttpRoomResource(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        self.putChild(b"list-leader", HttpListIdentityResource())


def install(root: resource.Resource):
    root.putChild(b"game", HttpRoomResource())
