import traceback

import discord
from discord.ext import commands
from discord.ext.commands import (
    BadArgument,
    CommandError,
    CommandNotFound,
    MissingPermissions,
)


class NoCurrenciesError(CommandError):
    pass


class CurrencyNotFoundError(CommandError):
    pass


class TooManyCurrenciesError(CommandError):
    def __init__(self, amount: int) -> None:
        self.amount = amount


class NotEnoughMoneyError(CommandError):
    pass


class SimilarCurrencyError(CommandError):
    pass


async def global_error_handler(
    ctx: commands.Context | discord.Interaction, error: Exception
) -> None:
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
            description=f"> You have reached the maximum amount of currencies (`{error.amount}`), remove some using `/currency remove`",
            color=discord.Color.red(),
        )
    elif isinstance(error, CommandNotFound):
        return
    elif isinstance(error, BadArgument):
        embed = discord.Embed(
            title="Bad argument",
            description=f"> {' '.join(error.args)}",
            color=discord.Color.red(),
        )
    elif isinstance(error, SimilarCurrencyError):
        embed = discord.Embed(
            title="Couldn't add currency",
            description=f"> A currency is already using that name or icon in this server",
            color=discord.Color.red(),
        )
    elif isinstance(error, MissingPermissions):
        embed = discord.Embed(
            title="Couldn't run command",
            description=f"> Missing permission `{'`, `'.join(error.missing_permissions)}`",
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

    if isinstance(ctx, commands.Context):
        await ctx.reply(embed=embed, mention_author=False, delete_after=40)
    else:
        await ctx.response.send_message(embed=embed, ephemeral=True, delete_after=40)
