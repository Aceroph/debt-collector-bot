from typing import TYPE_CHECKING

from discord.ext import commands

from services.config import Config
from services.currency import Currency
from utils.context import Context
from utils.errors import CurrencyNotFoundError

if TYPE_CHECKING:
    from main import App


class CurrencyConverter(commands.Converter):
    async def convert(self, ctx: commands.Context["App"], argument: str) -> Currency:
        assert isinstance(ctx, Context)
        async with ctx.bot.pool.acquire() as con:
            config = await Config.get(ctx)
            pattern = "%" + argument + "%"
            record = await con.fetchrow(
                "SELECT * FROM currencies WHERE id = any($1::integer[]) AND (icon ILIKE = $2 OR name ILIKE = $2);",
                config.currencies,
                pattern,
            )

            if not record:
                raise CurrencyNotFoundError

            return Currency(record)
