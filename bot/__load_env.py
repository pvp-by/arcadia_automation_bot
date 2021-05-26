from os import getenv
from dotenv import load_dotenv

LOCALS_IMPORTED = False

if not getenv("BOT_TOKEN", False):
    load_dotenv()
    LOCALS_IMPORTED = True
