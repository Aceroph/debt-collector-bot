from typing import TYPE_CHECKING, List, Self

import discord
from asyncpg import Record
from discord.ext import commands

from utils.errors import CurrencyNotFoundError

if TYPE_CHECKING:
    from main import DebtBot


class Currency:
    """
    A currency.

    Attributes
    ----------
    info_short : str
        Returns the currency in a pretty and short format.
    owner_mention : str
        Returns the owner as a mention for discord.
    name : str
        Returns the name of the currency.
    icon : str
        Returns the icon of the currency.
    id : int
        Returns the id of the currency.
    owner_id : int
        Returns the id of the owner of the currency.
    created_at : str
        Returns the date of its creation in a discord time format.
    hidden : bool
        Whether or not the currency is hidden.
    """

    def __init__(self, ctx: commands.Context["DebtBot"], record: Record) -> None:
        self._ctx = ctx
        self._id = record["id"]
        self._name = record["name"]
        self._icon = record["icon"]
        self._owner = record["owner"]
        self._hidden = record["hidden"]
        self._created_at = record["created_at"]
        self._allowed_roles = record["allowed_roles"] or []

    def __str__(self) -> str:
        return f"`#{self.id}` {self.name} - {self.icon}"

    @property
    def owner_mention(self) -> str:
        return f"<@{self.owner_id}>"

    @property
    def name(self) -> str:
        return self._name

    @property
    def icon(self) -> str:
        return self._icon

    @property
    def id(self) -> int:
        return self._id

    @property
    def owner_id(self) -> int:
        return self._owner

    @property
    def created_at(self) -> str:
        return discord.utils.format_dt(self._created_at, "R")

    @property
    def hidden(self) -> bool:
        return self._hidden

    @property
    def allowed_roles(self) -> List[int]:
        return self._allowed_roles

    async def get_uses(self) -> int:
        """
        Returns
        -------
        int
            The amount of accounts using this currency.
        """
        async with self._ctx.bot.pool.acquire() as con:
            return await con.fetchval(
                "SELECT COUNT(*) FROM banks WHERE currencyid = $1;", self.id
            )

    @classmethod
    async def get(cls, ctx: commands.Context["DebtBot"], id: int) -> Self:
        """
        Gets a currency.

        Parameters
        ----------
        ctx : Context
            The context of the command.
        id : int
            The id of the currency.

        Returns
        -------
        Currency
            The currency requested.

        Raises
        ------
        CurrencyNotFoundError
            If the currency does not exist or is hidden.
        """
        async with ctx.bot.pool.acquire() as con:
            record = await con.fetchrow("SELECT * FROM currencies WHERE id = $1;", id)
            if not record:
                raise CurrencyNotFoundError
            return cls(ctx, record)

    @classmethod
    async def get_user_currencies(
        cls, ctx: commands.Context["DebtBot"], user: discord.User | int
    ) -> List[Self]:
        """
        Gets all currencies owned by the user.

        Parameters
        ----------
        ctx : Context
            The context of the command.
        user : discord.User | int
            The user who owns the currencies.

        Returns
        -------
        List[Currency]
            The currencies owned by the user.
        """
        async with ctx.bot.pool.acquire() as con:
            id = user.id if isinstance(user, discord.User) else user
            records = await con.fetch("SELECT * FROM currencies WHERE owner = $1", id)
            return [cls(ctx, record) for record in records]
