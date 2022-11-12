class User:
    def __init__(self, id, lang='ru', town=None, town_name=None):
        self.id = id
        self.lang = lang
        self.town = town
        self.town_name = town_name
        self._commands = []

    def get_cmd_stack(self):
        if len(self._commands) > 0:
            return self._commands[-1]

    def set_cmd_stack(self, cmd_stack):
        if not isinstance(cmd_stack, (list, tuple)):
            self._commands.append((cmd_stack, ))
        else:
            self._commands.append(cmd_stack)

    cmd_stack = property(get_cmd_stack, set_cmd_stack)

    def cmd_stack_pop(self):
        if len(self._commands) > 0:
            return self._commands.pop()
