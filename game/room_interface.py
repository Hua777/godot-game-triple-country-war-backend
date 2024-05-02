from game.socket_user_for_room_interface import SocketUserForRoomInterface


class RoomInterface:
    def __init__(self, id: str) -> None:
        self.id = id
        self.users: list[SocketUserForRoomInterface] = []

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
