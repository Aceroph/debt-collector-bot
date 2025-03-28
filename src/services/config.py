import functools
import json
from typing import Callable, List, Self

import discord
from asyncpg import Record
from discord.ext.commands import MissingPermissions

from services.currency import Currency
from utils.context import Context
from utils.errors import NoCurrenciesError, TooManyCurrenciesError


class Config:
    """
    The guild's config.

    Attributes
    ----------
    currencies : List[int]
        The currencies in the guild.
    """

    def __init__(self, ctx: "Context", record: Record) -> None:
        self._currencies = record["currencies"]
        self._ctx = ctx

    @property
    def currencies(self) -> List[int]:
        return self._currencies

    async def get_currencies(self) -> List[Currency]:
        """
        Gets all the currencies.

        Returns
        -------
        List[Currency]
            A list of currencies.

        Raises
        ------
        NoCurrenciesError
            No currencies were found, quite rare.
        """
        async with self._ctx.bot.pool.acquire() as con:
            records = await con.fetch(
                "SELECT * FROM currencies WHERE id = any($1::integer[]);",
                self.currencies,
            )
            return [Currency(r) for r in records]

    @classmethod
    async def get(cls, ctx: Context) -> Self:
        """
        Gets or creates a config for the guild.

        Parameters
        ----------
        ctx : Context
            The context of the command.

        Returns
        -------
        Config
            The config for the server.
        """
        assert ctx.guild
        async with ctx.bot.pool.acquire() as con:
            record = await con.fetchrow(
                "SELECT * FROM guildconfigs WHERE id = $1;", ctx.guild.id
            )

            # If no config exist, create a new one
            if not record:
                record = await con.fetchrow(
                    "INSERT INTO guildconfigs (id) VALUES ($1) RETURNING config;",
                    ctx.guild.id,
                )

            return cls(ctx, record)

    async def add_currency(
        self,
        currency: Currency | int,
    ) -> None:
        """
        Adds a currency to the guild.

        Parameters
        ----------
        currency : Currency | int
            The currency to add.

        Raises
        ------
        TooManyCurrenciesError
            If you exceed the maximum amount of currencies per-guild.
        """
        assert self._ctx.guild
        currency = (
            currency
            if isinstance(currency, Currency)
            else await Currency.get(self._ctx, currency)
        )

        if not Context.is_sudo(self._ctx.message):
            currencies = await self.get_currencies()
            if len(currencies) == 5:
                raise TooManyCurrenciesError

        async with self._ctx.bot.pool.acquire() as con:
            await con.execute(
                """UPDATE guildconfigs SET currencies = array_append(currencies, $1) WHERE id = $2;""",
                currency.id,
                self._ctx.guild.id,
            )

        embed = discord.Embed(
            title="Added currency to guild",
            description=f"> [+] ({currency.icon}) {currency.name}",
            color=discord.Color.gold(),
        )
        await self._ctx.reply(embed=embed, mention_author=False)

    async def remove_currency(
        self,
        currency: Currency | int,
    ) -> None:
        """
        Removes a currency from the guild.

        Parameters
        ----------
        currency : Currency | int
            The currency to remove.

        Raises
        ------
        NoCurrenciesError
            If the guild does not have any currencies or the currency is not even in the guild.
        """
        assert self._ctx.guild
        currency = (
            currency
            if isinstance(currency, Currency)
            else await Currency.get(self._ctx, currency)
        )

        config = await Config.get(self._ctx)
        if not currency.id in config.currencies:
            raise NoCurrenciesError

        async with self._ctx.bot.pool.acquire() as con:
            await con.execute(
                """UPDATE guildconfigs SET currencies = array_remove(currencies, $1) WHERE id = $2;""",
                currency.id,
                self._ctx.guild.id,
            )

        embed = discord.Embed(
            title="Removed currency to guild",
            description=f"> [-] ({currency.icon}) {currency.name}",
            color=discord.Color.gold(),
        )
        await self._ctx.reply(embed=embed, mention_author=False)

    @classmethod
    def has_permission(cls, permission: str):
        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                ctx: Context | discord.Interaction = args[1]
                author = ctx.author if isinstance(ctx, Context) else ctx.user
                message = ctx.message if isinstance(ctx, Context) else None

                match permission:
                    case "manage_currencies":
                        currency = None
                        for arg in args:
                            if isinstance(arg, Currency):
                                currency = arg
                        if not currency:
                            currency = args[0].currency

                        assert isinstance(author, discord.Member) and ctx.guild
                        if (
                            ctx.guild.owner_id == author.id
                            or Context.is_sudo(message)
                            or any(
                                [
                                    role in currency.allowed_roles
                                    for role in author.roles
                                ]
                            )
                        ):
                            await func(*args, **kwargs)
                        else:
                            raise MissingPermissions(["manage_currencies"])
                    case other_permission:
                        raise MissingPermissions([other_permission])

            return wrapper

        return decorator
