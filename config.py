import os
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

BOT_ID = os.getenv('BOT_ID')

TELETHON_ID = os.getenv('TELETHON_ID')
TELETHON_HASH = os.getenv('TELETHON_HASH')
TELETHON_PHONE = os.getenv('TELETHON_PHONE')

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_CHARSET = os.getenv('DB_CHARSET')
DB_PORT = os.getenv('DB_PORT')
