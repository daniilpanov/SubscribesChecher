import aiogram
from aiogram import Bot, Dispatcher

import typing

from aiogram.types import User

from Dialogs import get_simple_answer
from DB import DB


class BotControl:
    bot: typing.Union[Bot, None]
    __disp: typing.Union[Dispatcher, None]
    __methods: typing.Union[typing.Dict[str, callable], None] = dict()
    __db_inst: DB

    def __init__(self, identification, db_inst):
        self.id = identification
        self.bot = Bot(identification)
        self.__disp = Dispatcher(self.bot)
        self.current_command: typing.Dict[int, typing.Union[BotControl.CurrentCommand, None]] = dict()
        self.__db_inst = db_inst

    def method_decorator(self, func):
        async def wrapper(*args, **kwargs):
            tg_user: User = kwargs['msg'].from_user
            user = self.__db_inst.select_query('SELECT `user_id` FROM `tg_users` WHERE `user_id`=%s', (tg_user.id,),
                                               True)
            data = [tg_user.id, kwargs['msg'].chat.id, tg_user.username, tg_user.first_name, tg_user.last_name]

            if user:
                data.append(tg_user.id)
                self.__db_inst.query(
                    '''UPDATE `tg_users` SET `user_id`=%s, `chat_id`=%s, `username`=%s, `first_name`=%s, `last_name`=%s
                     WHERE `user_id`=%s''',
                    data,
                )
            else:
                self.__db_inst.query(
                    '''INSERT INTO `tg_users` (`user_id`, `chat_id`, `username`, `first_name`, `last_name`)
                     VALUE (%s, %s, %s, %s, %s)''',
                    data,
                )

            return await func(*args, **kwargs)

        return wrapper

    async def start(self):
        self.__disp.register_message_handler(self.command, regexp=r'\/.+')
        self.__disp.register_message_handler(self.message)
        await self.__disp.start_polling()

    def register(self, func: callable, key: str):
        self.__methods[key] = self.method_decorator(func)

    async def cmd_failure(self, msg):
        # This command is not supported in this context. Please, try again
        await self.bot.send_message(msg.chat.id, get_simple_answer('fail_cmd'))

    async def msg_failure(self, msg):
        # This message is unknown. Please, try again
        await self.bot.send_message(msg.chat.id, get_simple_answer('fail_msg'))

    async def command(self, msg: aiogram.types.Message):
        user_id = msg.from_user.id
        if user_id in self.current_command and self.current_command[user_id]:
            return await self.message(msg)

        cmd = msg.text[1:]
        self.current_command[user_id] = self.CurrentCommand(cmd, msg)

        if cmd in self.__methods:
            if not await self.__methods[cmd](self=self, msg=msg):
                self.current_command[user_id] = None
        else:
            await self.cmd_failure(msg)
            self.current_command[user_id] = None

    async def message(self, msg: aiogram.types.Message):
        user_id = msg.from_user.id
        if user_id in self.current_command and self.current_command[user_id]:
            if not await self.__methods[self.current_command[user_id].command](self=self, msg=msg):
                self.current_command[user_id] = None
        else:
            await self.msg_failure(msg)

    class CurrentCommand:
        command: typing.Union[str, None]
        data: typing.Dict = dict()
        state: int = 0
        msg: aiogram.types.Message

        def __init__(self, cmd, msg):
            self.command = cmd
            self.msg = msg

        def set(self, key, val):
            self.data[key] = val

        def get(self, key):
            return self.data[key] if key in self.data else None
