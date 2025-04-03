from typing import TYPE_CHECKING, List, Literal

import discord
from asyncpg import Pool
from discord import app_commands
from discord.ext import commands

from services.config import Config
from services.currency import Currency
from utils.errors import CurrencyNotFoundError

if TYPE_CHECKING:
    from main import DebtBot


class CurrencyConverter(commands.Converter):
    def __init__(self, scope: Literal["owned", "guild", "all"] = "all") -> None:
        self.scope = scope

    async def convert(
        self, ctx: commands.Context["DebtBot"], argument: str
    ) -> Currency:
        async with ctx.bot.pool.acquire() as con:
            config = await Config.get(ctx)

            try:
                return await Currency.get(ctx, int(argument))
            except ValueError:
                pass

            match self.scope:
                case "owned":
                    record = await con.fetchrow(
                        "SELECT * FROM currencies WHERE owner = $1 AND (icon ILIKE $1 OR name ILIKE $1);",
                        ctx.author.id,
                    )

                case "guild":
                    record = await con.fetchrow(
                        "SELECT * FROM currencies WHERE id = any($1::integer[]) AND (icon ILIKE $1 OR name ILIKE $1);",
                        config.currencies,
                    )

                case "all":
                    record = await con.fetchrow(
                        "SELECT * FROM currencies AND (icon ILIKE $1 OR name ILIKE $1);",
                    )

                case _:
                    record = None

            if not record:
                raise CurrencyNotFoundError

            return Currency(ctx, record)


async def currency_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    pattern = f"%{current}%"
    pool: Pool = getattr(interaction.client, "pool")
    async with pool.acquire() as con:
        records = await con.fetch(
            "SELECT id, name FROM currencies WHERE name ILIKE $1 OR icon ILIKE $2 LIMIT 25;",
            pattern,
            current,
        )

        return [
            app_commands.Choice(name=record["name"], value=str(record["id"]))
            for record in records
        ]
