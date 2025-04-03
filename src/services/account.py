from typing import TYPE_CHECKING, Dict, Optional, Self

from asyncpg import Record
from discord.abc import User
from discord.ext import commands
from discord.ext.commands import NotOwner

from services.config import Config
from services.currency import Currency
from utils.errors import NoCurrenciesError

if TYPE_CHECKING:
    from main import DebtBot


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

    def __init__(self, ctx: commands.Context["DebtBot"], record: Record) -> None:
        self._ctx = ctx
        self._wallet = record["wallet"]
        self._bank = record["bank"]
        self._userid = record["userid"]
        self._currency = record["currencyid"]

    @property
    def wallet(self) -> int:
        return self._wallet

    @property
    def bank(self) -> int:
        return self._bank

    @property
    def id(self) -> int:
        return self._userid

    @classmethod
    async def get(
        cls,
        ctx: commands.Context["DebtBot"],
        user: User | int,
        currency: Currency | int,
    ) -> Self:
        """
        Returns an account of the specified currency.

        Parameters
        ----------
        ctx : Context
            The context of the command.
        user : User | int
            The user owning the requested account.
        currency : Currency | int
            The currency to look for.

        Returns
        -------
        Account
            The account of the specified currency.
        """
        account_id = user if isinstance(user, int) else user.id
        currency_id = currency.id if isinstance(currency, Currency) else currency

        async with ctx.bot.pool.acquire() as con:
            record = await con.fetchrow(
                "SELECT * FROM banks WHERE userid = $1 AND currencyid = $2;",
                account_id,
                currency_id,
            )

            # Create an account for each currency if the member has none
            if not record:
                record = await con.fetchrow(
                    "INSERT INTO banks (userid, currencyid) VALUES ($1, $2) RETURNING *;",
                    account_id,
                    currency_id,
                )

            return cls(ctx, record)

    @classmethod
    async def get_all(
        cls, ctx: commands.Context["DebtBot"], user: User | int
    ) -> Dict[int, Self]:
        """
        Returns all accounts under the user's name

        Parameters
        ----------
        ctx : Context
            The context of the command.
        user : User | int
            The user owning the requested accounts.

        Returns
        -------
        List[Account]
            A list of the user's accounts
        """
        account_id = user if isinstance(user, int) else user.id

        async with ctx.bot.pool.acquire() as con:
            config = await Config.get(ctx)
            if len(config.currencies) == 0:
                raise NoCurrenciesError

            records = await con.fetch(
                "SELECT * FROM banks WHERE userid = $1 AND currencyid = any($2::integer[]);",
                account_id,
                config.currencies,
            )

            # Create missing accounts
            missing = config.currencies.copy()
            for record in records:
                id = record["currencyid"]
                if id in missing:
                    missing.remove(record["currencyid"])

            for id in missing:
                insert = await con.prepare(
                    "INSERT INTO banks (userid, currencyid) VALUES ($1, $2) RETURNING *;"
                )
                records.append(await insert.fetchrow(account_id, id))

            return {r["currencyid"]: cls(ctx, r) for r in records}

    async def add_money(
        self,
        amount: int,
        to_wallet: bool = True,
        reason: Optional[str] = None,
    ) -> None:
        """
        Adds money to an account.

        Parameters
        ----------
        amount : Decimal | float | int
            The amount to add, if negative, it will be removed.
        to_wallet : bool = True
            Whether to add the money to the account's wallet or bank.
        reason : str
            The reason for this transaction.
        """
        async with self._ctx.bot.pool.acquire() as con:
            if to_wallet:
                record = await con.fetchrow(
                    "UPDATE banks SET wallet = wallet + $1 WHERE currencyid = $2 AND userid = $3 RETURNING *;",
                    amount,
                    self._currency,
                    self.id,
                )
            else:
                record = await con.fetchrow(
                    "UPDATE banks SET bank = bank + $1 WHERE currencyid = $2 AND userid = $3 RETURNING *;",
                    amount,
                    self._currency,
                    self.id,
                )

            self.__init__(self._ctx, record)

    async def transfer_money(
        self,
        amount: int,
        target: Optional[Self | User] = None,
        to_wallet: bool = True,
        reason: Optional[str] = None,
    ) -> None:
        """
        Transfers money from an account to another.

        Parameters
        ----------
        amount : Decimal | float | int
            The amount to transfer
        target : Optional[Self | User] = None
            The account to transfer to, defaults to your own.
        to_wallet : bool = True
            Wheter to transfer from your wallet to your bank or vice-versa, only use this parameter if transfering to yourself.
        reason : Optional[str]
            The reason for the transfer
        """
        if isinstance(target, User):
            target = await self.__class__.get(self._ctx, target, self._currency)

        if target and target.id != self.id:
            if not to_wallet:
                raise NotOwner("You can not transfer money to somebody else's bank !")

            await self.add_money(-amount, True, reason)
            await target.add_money(amount, True, reason)

        else:
            await self.add_money(-amount, not to_wallet, reason)
            await self.add_money(amount, to_wallet, reason)
