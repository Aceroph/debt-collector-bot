from sys import getsizeof
from typing import TYPE_CHECKING, Dict, List, Optional

from discord import User
from discord.ext.commands import Context

from services import Config, Currency

if TYPE_CHECKING:
    from main import DebtBot


class Cache:
    def __init__(self) -> None:
        self._guild_currencies: Dict[int, List[Currency]] = {}
        self._user_currencies: Dict[int, List[Currency]] = {}

    def get_total_guilds(self) -> int:
        """Returns the number of guild currencies in cache"""
        return len(self._guild_currencies)

    def get_total_users(self) -> int:
        """Returns the number of user currencies in cache"""
        return len(self._guild_currencies)

    def sizeof_guilds(self) -> int:
        """Returns the size of the cached guild currencies"""
        return getsizeof(self._guild_currencies)

    def sizeof_users(self) -> int:
        """Returns the size of the cached user currencies"""
        return getsizeof(self._user_currencies)

    async def get_guild_currencies(self, ctx: Context["DebtBot"]) -> List[Currency]:
        """
        Returns the currencies within the guild/DM.

        Parameters
        ----------
        ctx : Context["DebtBot"]
            The context of the command.

        Returns
        -------
        List[Currency]
            The list of currencies within the guild/DM.
        """
        id = (ctx.guild or ctx.author).id
        currencies = self._guild_currencies.get(id)

        if not currencies:
            config = await Config.get(ctx)
            currencies = await config.get_currencies()
            self._guild_currencies[id] = currencies

        return currencies

    async def get_user_currencies(
        self, ctx: Context["DebtBot"], user: Optional[User | int] = None
    ) -> List[Currency]:
        """
        Returns the currencies owned by the user.

        Parameters
        ----------
        ctx : Context["DebtBot"]
            The context of the command.
        user : Optional[User]=None
            The user who owns the currencies, defaults to command author.

        Returns
        -------
        List[Currency]
            The currencies owned by the user.
        """
        id = user.id if isinstance(user, User) else user if user else ctx.author.id
        currencies = self._user_currencies.get(id)

        if not currencies:
            currencies = await Currency.get_user_currencies(ctx, id)

        return currencies
