from typing import TYPE_CHECKING, List

import discord
from discord import app_commands
from discord.ext.commands import Context

if TYPE_CHECKING:
    from main import DebtBot


async def user_currencies(
    interaction: discord.Interaction["DebtBot"],
    _: str,
) -> List[app_commands.Choice[str]]:
    ctx = await Context.from_interaction(interaction)
    currencies = await interaction.client.cache.get_user_currencies(ctx)
    return [
        app_commands.Choice(name=currency.name, value=str(currency.id))
        for currency in currencies
    ]


async def guild_currencies(
    interaction: discord.Interaction["DebtBot"], current: str
) -> List[app_commands.Choice[str]]:
    ctx = await Context.from_interaction(interaction)
    currencies = await interaction.client.cache.get_guild_currencies(ctx)
    return [
        app_commands.Choice(name=currency.name, value=str(currency.id))
        for currency in currencies
        if currency.name.lower().startswith(current.lower())
    ]
