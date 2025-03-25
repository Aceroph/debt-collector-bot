import os

import discord
from discord.ext import commands

from modules import EXTENSIONS


class App(commands.Bot):
    def __init__(self, intents: discord.Intents) -> None:
        super().__init__("$", intents=intents)

    async def setup_hook(self) -> None:
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
