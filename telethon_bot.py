import typing

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

from config import TELETHON_ID, TELETHON_HASH, TELETHON_PHONE


telethon_client: typing.Union[TelegramClient, None] = None


async def telethon_init():
    global telethon_client
    try:
        with open('session.dat') as file:
            session = file.readline()[:-1]
    except FileNotFoundError:
        with open('session.dat', 'w'):
            session = None
    finally:
        telethon_client = TelegramClient(StringSession(session) if session else StringSession(), TELETHON_ID,
                                         TELETHON_HASH)
        await telethon_client.connect()

        if not await telethon_client.is_user_authorized():
            await telethon_client.send_code_request(TELETHON_PHONE or input('Enter your phone: '))
            try:
                await telethon_client.sign_in(TELETHON_PHONE, input('Enter the code: '))
            except SessionPasswordNeededError:
                await telethon_client.sign_in(password=input('Password: '))

        if not session:
            with open('session.dat', 'w') as f:
                session = telethon_client.session.save()
                print(session, file=f)


