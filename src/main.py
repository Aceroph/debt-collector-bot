import os
from typing import List

import asyncpg
import discord
from discord.ext import commands

from modules import EXTENSIONS
from utils import errors


def prefix(bot: "App", msg: discord.Message) -> List[str]:
    if msg.author.id == bot.owner_id:
        return ["$", "sudo ", "Sudo ", "SUDO "]
    else:
        return ["$"]


class App(commands.Bot):
    def __init__(self, intents: discord.Intents) -> None:
        super().__init__(prefix, intents=intents)
        self.pool: asyncpg.Pool
        self.on_command_error = errors.global_error_handler

    async def setup_hook(self) -> None:
        # Setup db pool
        password = os.environ.get("DB_PASSWORD") or "postgres"
        database = os.environ.get("DB_NAME") or "postgres"
        user = os.environ.get("DB_USER") or "postgres"
        host = os.environ.get("DB_HOST") or "localhost"
        port = os.environ.get("DB_PORT") or 5432

        pool = await asyncpg.create_pool(
            database=database, user=user, host=host, port=port, password=password
        )
        assert pool
        self.pool = pool

        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
            except:
                print(f"Failed to load extension {ext}")


if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True

    bot = App(intents=intents)

    token = os.environ.get("TOKEN")
    if not token:
        raise Exception("Missing TOKEN")
    bot.run(token)
