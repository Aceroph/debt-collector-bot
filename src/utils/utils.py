from typing import TYPE_CHECKING, Union

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from main import DebtBot


def get_accent_color(user: Union[discord.User, discord.Member]) -> discord.Color:
    """
    Returns either the user's top role color, their accent color or white.

    Parameters
    ----------
    user : Union[discord.User, discord.Member]
        The user to get the color from.

    Returns
    -------
    discord.Color
        The color of the user.
    """
    color = discord.Color.default()

    if isinstance(user, discord.Member):
        color = user.top_role.color

    if color == discord.Color.default():
        color = user.accent_color or discord.Color.light_embed()

    return color


def is_sudo(ctx: commands.Context["DebtBot"]) -> bool:
    """
    Checks if the command was run as sudo, meaning the user is trying to run with elevated privileges.

    Parameters
    ----------
    ctx : commands.Context["DebtBot"]
        The context of the invokation.

    Returns
    -------
    bool
        Whether the command was run with elevated privileges.

    Note
    ----
    ctx
        Only the bot's owner can do so.
    """
    return ctx.bot.is_owner(ctx.author) and ctx.message.content.lower().startswith(
        "sudo"
    )
