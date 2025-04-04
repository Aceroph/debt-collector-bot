import logging
import os
from typing import List

import asyncpg
import discord
from asyncpg.connection import traceback
from discord.ext import commands

import services.cache as cache
from cogs import EXTENSIONS
from utils import errors


def prefix(bot: "DebtBot", msg: discord.Message) -> List[str]:
    if msg.author.id == bot.owner_id:
        return [bot.base_prefix, "sudo ", "Sudo ", "SUDO "]
    else:
        return [bot.base_prefix]


class DebtBot(commands.Bot):
    owner_id = 493107597281329185

    def __init__(self, intents: discord.Intents) -> None:
        super().__init__(prefix, intents=intents)
        self.pool: asyncpg.Pool
        self.cache = cache.Cache()
        self.on_command_error = errors.global_error_handler
        self.logger = logging.getLogger("discord")
        self.base_prefix = os.environ.get("BOT_PREFIX", "$")

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
                self.logger.info("Loaded extension %s", ext)
            except Exception as err:
                self.logger.error(
                    f"Failed to load extension %s : %s",
                    ext,
                    "".join(
                        traceback.format_exception(type(err), err, err.__traceback__)
                    ),
                )


if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True

    bot = DebtBot(intents=intents)

    token = os.environ.get("TOKEN")
    if not token:
        raise Exception("Missing TOKEN")
    bot.run(token)
