class WrongResponseType(Exception):
    """Getting response not in dictionary form."""


class MissingHomeworkKey(Exception):
    """Homeworks key is missing in response dictionary."""


class HomeworksNotInList(Exception):
    """Getting homeworks not in list."""
