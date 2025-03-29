from discord.ext import commands

from services.config import Config
from services.currency import Currency
from utils.context import Context
from utils.errors import CurrencyNotFoundError


class CurrencyConverter(commands.Converter):
    def __init__(self, is_owned: bool = False) -> None:
        self._is_owned = is_owned

    async def convert(self, ctx: Context, argument: str) -> Currency:  # type: ignore
        async with ctx.bot.pool.acquire() as con:
            config = await Config.get(ctx)
            pattern = f"%{argument}%"
            if self._is_owned:
                record = await con.fetchrow(
                    "SELECT * FROM currencies WHERE owner = $1 AND ( icon ILIKE $2 OR name ILIKE $3 );",
                    ctx.author.id,
                    argument,
                    pattern,
                )
            else:
                record = await con.fetchrow(
                    "SELECT * FROM currencies WHERE id = any($1::integer[]) AND ( icon ILIKE $2 OR name ILIKE $3 );",
                    config.currencies,
                    argument,
                    pattern,
                )

            if not record:
                try:
                    return await Currency.get(ctx, int(argument))
                except ValueError:
                    raise CurrencyNotFoundError

            return Currency(ctx, record)
