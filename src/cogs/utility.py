from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from main import App


class Utility(commands.Cog):
    def __init__(self, bot: "App") -> None:
        self.bot = bot

    @commands.hybrid_command()
    async def ping(self, ctx: commands.Context):
        """Simplest command, ping \N{TABLE TENNIS PADDLE AND BALL}"""
        embed = discord.Embed(
            title="Pong \N{TABLE TENNIS PADDLE AND BALL}",
            description=f">>> WS: `{round(self.bot.latency * 1000)}ms`",
            color=discord.Color.blurple(),
        )
        return await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: "App") -> None:
    await bot.add_cog(Utility(bot))
