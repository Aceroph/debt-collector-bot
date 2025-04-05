import re
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


async def currency_with_amount(
    interaction: discord.Interaction["DebtBot"], current: str
) -> List[app_commands.Choice[str]]:
    ctx = await Context.from_interaction(interaction)
    currencies = await interaction.client.cache.get_guild_currencies(ctx)

    match = re.match(r"([0-9,.]+) *([a-zA-Z ]+)?", current)
    if not match:
        return [
            app_commands.Choice(
                name=f"0 {currencies[0].name}", value=f"0 {currencies[0].name}"
            )
        ]

    amount, query = match.groups()

    return [
        app_commands.Choice(
            name=f"{int(amount):,} {currency.name}", value=f"{amount} {currency.name}"
        )
        for currency in currencies
        if not query or query.lower() in currency.name.lower() or query == currency.icon
    ]
