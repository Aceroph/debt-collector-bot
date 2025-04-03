from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from main import DebtBot


class Utility(commands.Cog):
    @commands.hybrid_command()
    async def ping(self, ctx: commands.Context["DebtBot"]):
        """Simplest command, ping \N{TABLE TENNIS PADDLE AND BALL}"""
        embed = discord.Embed(
            title="Pong \N{TABLE TENNIS PADDLE AND BALL}",
            description=f">>> WS: `{round(ctx.bot.latency * 1000)}ms`",
            color=discord.Color.blurple(),
        )
        return await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: "DebtBot") -> None:
    await bot.add_cog(Utility())
