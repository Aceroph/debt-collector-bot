from decimal import Decimal
from typing import Dict, Self

from asyncpg import Record
from discord import Member

from services.config import Config
from services.currency import Currency
from utils.context import Context


class Account:
    """
    An account under a currency with a wallet and a bank.

    Attributes
    ----------
    wallet : float
        The current amount of money in their wallet.
    bank : float
        The current amount of money in their bank.
    """

    def __init__(self, ctx: Context, record: Record) -> None:
        self._ctx = ctx
        self._wallet = record["wallet"]
        self._bank = record["bank"]
        self._userid = record["userid"]
        self._currency = record["currencyid"]

    @property
    def wallet(self) -> Decimal:
        return self._wallet

    @property
    def bank(self) -> Decimal:
        return self._bank

    @classmethod
    async def get(cls, ctx: Context, member: Member, currency: Currency | int) -> Self:
        """
        Returns an account of the specified currency.

        Parameters
        ----------
        ctx : Context
            The context of the command.
        member : Member
            The member owning the requested account.
        currency : Currency | int
            The currency to look for.

        Returns
        -------
        Account
            The account of the specified currency.
        """
        currency_id = currency.id if isinstance(currency, Currency) else currency
        async with ctx.bot.pool.acquire() as con:
            record = await con.fetchrow(
                "SELECT * FROM banks WHERE userid = $1 AND currencyid = $3;",
                member.id,
                currency_id,
            )

            # Create an account for each currency if the member has none
            if len(record) == 0:
                record = await con.fetchrow(
                    "INSERT INTO banks (userid, currencyid) VALUES ($1, $2) RETURNING *;",
                    member.id,
                    currency_id,
                )

            return cls(ctx, record)

    @classmethod
    async def get_all(cls, ctx: Context, member: Member) -> Dict[int, Self]:
        """
        Returns all accounts under the member's name

        Parameters
        ----------
        ctx : Context
            The context of the command.
        member : Member
            The member owning the requested accounts.

        Returns
        -------
        List[Account]
            A list of the member's accounts
        """
        async with ctx.bot.pool.acquire() as con:
            records = await con.fetch(
                "SELECT * FROM banks WHERE userid = $1;",
                member.id,
            )
            config = await Config.get(ctx)

            # Create an account for each currency if the member has none
            if len(records) < len(config.currencies):
                insert = await con.prepare(
                    "INSERT INTO banks (userid, currencyid) VALUES ($1, $2) RETURNING *;"
                )
                records = [
                    await insert.fetchrow(ctx.author.id, c_id)
                    for c_id in config.currencies
                ]

            return {r["currencyid"]: cls(ctx, r) for r in records}
