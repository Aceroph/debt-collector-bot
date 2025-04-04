import functools
from typing import TYPE_CHECKING, Callable, List, Self

import discord
from asyncpg import Record
from discord.ext import commands
from discord.ext.commands import MissingPermissions

import utils
from services import Currency
from utils.errors import NoCurrenciesError, SimilarCurrencyError, TooManyCurrenciesError

if TYPE_CHECKING:
    from main import DebtBot


class Config:
    """
    The guild's config.

    Attributes
    ----------
    currencies : List[int]
        The currencies in the guild.
    """

    def __init__(self, ctx: commands.Context["DebtBot"], record: Record) -> None:
        self._currencies = record["currencies"]
        self._ctx = ctx

    @property
    def max_currencies(self) -> int:
        return 5 if self._ctx.guild else 1

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
            return [Currency(self._ctx, r) for r in records]

    @classmethod
    async def get(cls, ctx: commands.Context["DebtBot"]) -> Self:
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
        currency = (
            currency
            if isinstance(currency, Currency)
            else await Currency.get(self._ctx, currency)
        )

        if any(
            [
                currency.icon == c.icon or currency.name == c.name
                for c in await self.get_currencies()
            ]
        ):
            raise SimilarCurrencyError

        if not utils.is_sudo(self._ctx) and len(self.currencies) == self.max_currencies:
            raise TooManyCurrenciesError(self.max_currencies)

        async with self._ctx.bot.pool.acquire() as con:
            await con.execute(
                """UPDATE guildconfigs SET currencies = array_append(currencies, $1) WHERE id = $2;""",
                currency.id,
                self._ctx.guild.id if self._ctx.guild else self._ctx.author.id,
            )

        embed = discord.Embed(
            title="Added currency to guild",
            description=f"> [+] ({currency.icon}) {currency.name}",
            color=utils.get_accent_color(self._ctx.author),
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
                self._ctx.guild.id if self._ctx.guild else self._ctx.author.id,
            )

        embed = discord.Embed(
            title="Removed currency to guild",
            description=f"> [-] ({currency.icon}) {currency.name}",
            color=utils.get_accent_color(self._ctx.author),
        )
        await self._ctx.reply(embed=embed, mention_author=False)

    @classmethod
    def has_permission(cls, permission: str):
        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                ctx: commands.Context["DebtBot"] | discord.Interaction = args[1]
                author = ctx.author if isinstance(ctx, commands.Context) else ctx.user

                match permission:
                    case "banker":
                        if isinstance(ctx, discord.Interaction):
                            currency: Currency = args[0].currency
                        elif len(ctx.args) > 0:
                            currency: Currency = [
                                arg for arg in ctx.args if hasattr(arg, "allowed_roles")
                            ][0]
                        else:
                            currency: Currency = ctx.kwargs["currency"]

                        if (
                            currency.owner_id == author.id
                            or isinstance(ctx, commands.Context)
                            and utils.is_sudo(ctx)
                            or isinstance(author, discord.Member)
                            and any(
                                [
                                    role in currency.allowed_roles
                                    for role in author.roles
                                ]
                            )
                        ):
                            await func(*args, **kwargs)
                        else:
                            raise MissingPermissions(["banker"])

                    case "manage_currencies":
                        if (
                            not ctx.guild
                            or ctx.guild
                            and ctx.guild.owner_id == author.id
                            or isinstance(ctx, commands.Context)
                            and utils.is_sudo(ctx)
                        ):
                            await func(*args, **kwargs)
                        else:
                            raise MissingPermissions(["manage_currencies"])

                    case other_permission:
                        raise MissingPermissions([other_permission])

            return wrapper

        return decorator
