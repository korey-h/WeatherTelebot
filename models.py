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
        if isinstance(cmd_stack, dict):
            self._commands.append(cmd_stack)
        else:
            KEYS = ('cmd_name', 'cmd', 'data', 'calling')
            if isinstance(cmd_stack, (list, tuple)):
                s = tuple(cmd_stack)
                values = s[:4] if len(s) >= 4 else s + (None, )
            else:
                values = (cmd_stack, cmd_stack, {}, None)
            self._commands.append(
                {key: val for key, val in zip(KEYS, values)}
            )

    cmd_stack = property(get_cmd_stack, set_cmd_stack)

    def cmd_stack_pop(self):
        if len(self._commands) > 0:
            return self._commands.pop()
