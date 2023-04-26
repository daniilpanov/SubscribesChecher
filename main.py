import asyncio
# Aiogram
import aiogram.types
from telethon.errors import UsernameInvalidError
import re
# Custom files
from DB import DB
from aiogram_bot import BotControl
from config import *
from Dialogs import dialogs, get_simple_answer
import telethon_bot

# Initialize DB connection and bot controller
db_connection = DB(DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_CHARSET, DB_PORT)
bot = BotControl(BOT_ID, db_connection)


# The main async function (this is really needle for sync methods calls by keyword 'await')
async def main():
    global db_connection, bot

    # Initialize telethon bot
    await telethon_bot.telethon_init()

    # -- Commands --
    # Just start
    async def start(self: BotControl, msg: aiogram.types.Message):
        await self.bot.send_message(msg.chat.id, get_simple_answer('start'))
        return False

    # Add user (3-steps: [cmd], username, channel_id)
    async def add_user(self: BotControl, msg: aiogram.types.Message):
        # Функция отмены
        if msg.text == '/back':
            await bot.bot.send_message(msg.chat.id, get_simple_answer('back'))
            # CLOSE THE COMMAND
            return False

        user_id = msg.from_user.id

        # State 0 always be excluded because the bot just send the hint message
        if self.current_command[user_id].state == 1:
            # a little validation...
            if msg.text[0] != '@':
                await self.bot.send_message(msg.chat.id, dialogs.get('add_user')['wrong'])
                # DO NOT CLOSE THE COMMAND
                return True
            # Write the data
            self.current_command[user_id].data['username'] = msg.text
        elif self.current_command[user_id].state == 2:
            # here is a little validation too
            if msg.text[0] != '@':
                await self.bot.send_message(msg.chat.id, dialogs.get('add_user')['wrong'])
                # DO NOT CLOSE THE COMMAND!!!
                return True
            # Write the data
            self.current_command[user_id].data['channel'] = msg.text
            data = self.current_command[user_id].data
            # Add an author for @@_personal access_@@
            data['author'] = msg.from_user.id
            # Write all the data to MySQL
            db_connection.query(
                'INSERT INTO `checklist`(`username`, `channel_id`, `author`) VALUE (%s, %s, %s)',
                list(data.values())
            )

        await self.bot.send_message(msg.chat.id, dialogs.get('add_user')[str(self.current_command[user_id].state)])
        self.current_command[user_id].state += 1
        return self.current_command[user_id].state < 3

    async def show_list(self: BotControl, msg: aiogram.types.Message):
        dialog = dialogs.get('show_list')
        await self.bot.send_message(msg.chat.id, dialog['wait'])

        users_list = db_connection.select_query(
            'SELECT * FROM `checklist` WHERE `author`=%s ORDER BY channel_id, id',
            (msg.from_user.id,),
        )
        response = ""

        for row in users_list:
            status = dialog['subscribed']
            try:
                user_entity = await telethon_bot.telethon_client.get_entity(row['username'])
                user_channel_status = await self.bot.get_chat_member(chat_id=row['channel_id'], user_id=user_entity.id)
                if user_channel_status["status"] == 'left':
                    status = dialog['unsubscribed']
            except aiogram.utils.exceptions.TelegramAPIError as ex:
                status = dialog['no_data'] if 'not found' in str(ex) else dialog['unsubscribed']
            except ValueError:
                status = dialog['no_data']
            except UsernameInvalidError:
                status = dialog['what']
            finally:
                response += row['username'] + " -- " + row['channel_id'] + ":  " + status + "\n"

        await self.bot.send_message(msg.chat.id, response or dialog['empty'])
        await self.bot.send_message(msg.chat.id, dialog['help'])

        return False

    async def show_list_bulk(self: BotControl, msg: aiogram.types.Message):
        # Функция отмены
        if msg.text == '/back':
            await bot.bot.send_message(msg.chat.id, get_simple_answer('back'))
            # CLOSE THE COMMAND
            return False

        user_id = msg.from_user.id

        if self.current_command[user_id].state == 0:
            await self.bot.send_message(msg.chat.id, dialogs.get('show_list_bulk')['0'])
        elif self.current_command[user_id].state == 1:
            # a little validation...
            if msg.text[0] != '@' and msg.text.strip() != '-':
                await self.bot.send_message(msg.chat.id, dialogs.get('add_user')['wrong'])
                # DO NOT CLOSE THE COMMAND
                return True
            # Write the data
            channel_id = msg.text.strip()

            dialog = dialogs.get('show_list')
            await self.bot.send_message(msg.chat.id, dialog['wait'])

            channels_list = db_connection.select_query(
                '''SELECT channel_id, GROUP_CONCAT(username) as users, author
                 FROM `checklist`
                 WHERE `author`=%s''' + (' AND `channel_id`=%s' if channel_id != '-' else '') + '''
                 GROUP BY channel_id
                 ORDER BY channel_id, id''',
                (msg.from_user.id, channel_id) if channel_id != '-' else (msg.from_user.id,),
            )

            if len(channels_list) > 0:
                for row in channels_list:
                    response = "Подписчики канала " + row['channel_id'] + ": \n\n"
                    users_list = row['users'].split(',')
                    for user in users_list:
                        status = dialog['subscribed']
                        try:
                            user_entity = await telethon_bot.telethon_client.get_entity(user)
                            user_channel_status = await self.bot.get_chat_member(
                                chat_id=row['channel_id'],
                                user_id=user_entity.id,
                            )
                            if user_channel_status["status"] == 'left':
                                status = dialog['unsubscribed']
                        except aiogram.utils.exceptions.TelegramAPIError as ex:
                            status = dialog['no_data'] if 'not found' in str(ex) else dialog['unsubscribed']
                        except ValueError:
                            status = dialog['no_data']
                        except UsernameInvalidError:
                            status = dialog['what']
                        finally:
                            response += user + ":  " + status + "\n"

                    await self.bot.send_message(msg.chat.id, response or dialog['empty'])
            else:
                await self.bot.send_message(msg.chat.id, dialog['empty'])

        self.current_command[user_id].state += 1
        return self.current_command[user_id].state < 2

    async def add_list(self: BotControl, msg: aiogram.types.Message):
        if msg.text == '/back':
            return False

        user_id = msg.from_user.id

        if self.current_command[user_id].state == 1:
            if msg.text[0] != '@':
                await self.bot.send_message(msg.chat.id, dialogs.get('add_list')['wrong'])
                return True
            self.current_command[user_id].data['channel'] = msg.text
        elif self.current_command[user_id].state == 2:
            rows = msg.text.split('@')[1:]
            values = ""
            params = []
            for i in rows:
                values += "(%s, %s, %s),"
                params.append('@' + i.strip())
                params.append(self.current_command[user_id].data['channel'])
                params.append(msg.from_user.id)

            db_connection.query(
                'INSERT INTO `checklist`(`username`, `channel_id`, `author`) VALUES ' + values[:-1],
                params,
            )

        await self.bot.send_message(msg.chat.id, dialogs.get('add_list')[str(self.current_command[user_id].state)])
        self.current_command[user_id].state += 1
        return self.current_command[user_id].state < 3

    async def add_list_bulk(self: BotControl, msg: aiogram.types.Message):
        if msg.text == '/back':
            return False

        user_id = msg.from_user.id

        if self.current_command[user_id].state == 1:
            # @channel_id - @username [ @user.... ]
            pattern = re.compile(
                r'\d*.? *(@[0-9a-zA-Z_]+) *- *(@[0-9a-zA-Z_]+) *(\[ *((@[0-9a-zA-Z_]+) *(( *, *| *и *| +) *(@[0-9a-zA-Z_]+))[^]]*)])?'
            )
            text = msg.text.splitlines()

            params = []
            ignored = []
            pre_data = db_connection.select_query(
                'SELECT CONCAT(username, channel_id) as item FROM `checklist` WHERE `author`=%s',
                (msg.from_user.id,),
            )
            pre_data = list(map(lambda x: x['item'], pre_data))

            for row in text:
                matches = pattern.findall(row)
                if len(matches) < 1:
                    ignored.append(row)
                    continue
                data = list(matches[0])
                users = re.split(r' *, *| *и *| +', data[3]) + [data[1]]
                channel_id = data.pop(0)
                for info in users:
                    # info = ''.join(re.split(r' *, *| *и *| +', info.strip()))
                    info = info.strip()
                    if not info or info[0] != '@':
                        continue
                    elif info + channel_id in pre_data:
                        continue
                    params.append(info)
                    params.append(channel_id)
                    params.append(msg.from_user.id)

            if len(params) > 0:
                db_connection.query(
                    'INSERT INTO `checklist`(`username`, `channel_id`, `author`) VALUES '
                    + ', '.join(['(%s, %s, %s)' for _ in range(len(params) // 3)]),
                    params,
                )

            if len(ignored) > 0:
                await self.bot.send_message(msg.chat.id, 'Проигнорированные строки: \n\n' + '\n'.join(ignored))

        dialog = dialogs.get('add_list_bulk')[str(self.current_command[user_id].state)]
        if type(dialog) is type(list()):
            for message in dialog:
                await self.bot.send_message(msg.chat.id, message)
        else:
            await self.bot.send_message(msg.chat.id, dialog)

        self.current_command[user_id].state += 1
        return self.current_command[user_id].state < 2

    bot.register(start, 'start')
    bot.register(add_user, 'adduser')
    bot.register(show_list, 'showlist')
    bot.register(show_list_bulk, 'showlistbulk')
    bot.register(add_list, 'addlist')
    bot.register(add_list_bulk, 'addlistbulk')

    # Stop app
    await bot.start()
    telethon_bot.telethon_client.disconnect()
    del db_connection


asyncio.run(main())
