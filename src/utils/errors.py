import traceback

import discord
from discord.ext import commands
from discord.ext.commands import CommandError


class NoCurrenciesError(CommandError):
    pass


class CurrencyNotFoundError(CommandError):
    pass


class TooManyCurrenciesError(CommandError):
    pass


async def global_error_handler(ctx: commands.Context, error: CommandError) -> None:
    if isinstance(error, NoCurrenciesError):
        embed = discord.Embed(
            title="No currencies in this guild",
            description="> Create or add one using `/currency`",
            color=discord.Color.red(),
        )
    elif isinstance(error, CurrencyNotFoundError):
        embed = discord.Embed(
            title="This currency does not exist",
            description="> Create it using `/currency`",
            color=discord.Color.red(),
        )
    elif isinstance(error, TooManyCurrenciesError):
        embed = discord.Embed(
            title="Too many currencies",
            description="> You have reached the maximum amount of currencies per-guild, remove some using `/currency remove`",
            color=discord.Color.red(),
        )
    else:
        # Unhandled error
        trace = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        embed = discord.Embed(
            title="Unhandled error !!",
            description=f">>> ```py\n{trace}```",
            color=discord.Color.red(),
        )

    await ctx.reply(embed=embed, mention_author=False, delete_after=40)
