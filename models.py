class User:
    def __init__(self, id, lang='ru', town=None):
        self.id = id
        self.lang = lang
        self.town = town
        self._commands = []

    def get_last_req(self):
        if len(self._commands) > 0:
            return self._commands.pop()

    def set_last_req(self, last_req):
        self._commands.append(last_req)

    last_req = property(get_last_req, set_last_req)
