import json
import io


class Dialogs:
    data: dict = dict()

    def __init__(self):
        with io.open('dialogs.json', mode='r', encoding='utf-8') as df:
            self.data = json.load(df)

    def get(self, key):
        return self.data[key] if key in self.data else None


dialogs = Dialogs()


def get_simple_answer(key):
    global dialogs
    return dialogs.get(key)
