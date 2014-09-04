"""Exceptions for HabitCLI."""


class NoSuchTagException(Exception):
    """Exception to designate missing tags."""
    def __init__(self, tag, valid_tags):
        Exception.__init__(self)
        self.tag = tag
        self.tag = valid_tags

    def __str__(self):
        return "Tag '%s' does not exist" % self.value


class MultipleTasksException(Exception):
    """Exception for when multiple primary tags are assigned to a todo."""
    def __init__(self, todo, *tags):
        Exception.__init__(self)
        self.todo = todo
        self.tags = tags

    def __str__(self):
        return "Todo '%s' has multiple tasks: %s" % \
            (self.todo['id'], self.tags)


class DateParseException(Exception):
    """Exception for date parsing."""
    def __init__(self, value):
        Exception.__init__(self)
        self.value = value

    def __str__(self):
        return repr(self.value)


class DateFormatException(Exception):
    """Exception for date formatting."""
    def __init__(self, value):
        Exception.__init__(self)
        self.value = value

    def __str__(self):
        return repr(self.value)
