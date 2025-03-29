from typing import TYPE_CHECKING, Literal, Optional

import discord
from discord.ext import commands

from utils import context

if TYPE_CHECKING:
    from main import App


class Admin(commands.Cog):
    @commands.is_owner()
    @commands.command()
    async def sql(self, ctx: context.Context, *, sql: str) -> None:
        async with ctx.bot.pool.acquire() as con:
            result = await con.fetch(sql)
            output = "\n".join(
                [", ".join([repr(x) for x in r.items()]) for r in result]
            )
            if len(output) == 0:
                output = "No output"

            await ctx.reply(output, mention_author=False)

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def sync(
        self,
        ctx: context.Context,
        guilds: commands.Greedy[discord.Object],
        spec: Optional[Literal["~", "*", "^"]] = None,
    ) -> None:
        """Syncs commands ig"""
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                assert ctx.guild
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


async def setup(bot: "App") -> None:
    await bot.add_cog(Admin())
