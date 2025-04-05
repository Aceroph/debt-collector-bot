from sys import getsizeof
from typing import TYPE_CHECKING, Dict, List

from discord import Guild, Member, User
from discord.ext.commands import Context

from services import Config, Currency

if TYPE_CHECKING:
    from main import DebtBot


class Cache:
    def __init__(self) -> None:
        self._guild_currencies: Dict[int, List[Currency]] = {}
        self._user_currencies: Dict[int, List[Currency]] = {}

    async def sync(
        self, ctx: Context["DebtBot"], synced: User | Member | Guild
    ) -> None:
        """
        Syncs the provided user/guild's cache with the database.

        Parameters
        ----------
        synced : User | Member | Guild
            Who to sync.
        """
        if isinstance(synced, User | Member):
            self._user_currencies[synced.id] = await Currency.get_user_currencies(
                ctx, synced.id
            )

        if isinstance(synced, Guild) or not ctx.guild:
            config = await Config.get(ctx)
            self._guild_currencies[synced.id] = await config.get_currencies()

    def get_total_guilds(self) -> int:
        """Returns the number of guild currencies in cache."""
        return len(self._guild_currencies)

    def get_total_users(self) -> int:
        """Returns the number of user currencies in cache."""
        return len(self._guild_currencies)

    def get_sizeof_guilds(self) -> int:
        """Returns the size of the cached guild currencies."""
        return getsizeof(self._guild_currencies)

    def get_sizeof_users(self) -> int:
        """Returns the size of the cached user currencies."""
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

    async def get_user_currencies(self, ctx: Context["DebtBot"]) -> List[Currency]:
        """
        Returns the currencies owned by the user.

        Parameters
        ----------
        ctx : Context["DebtBot"]
            The context of the command.

        Returns
        -------
        List[Currency]
            The currencies owned by the user.
        """
        currencies = self._user_currencies.get(ctx.author.id)

        if not currencies:
            currencies = await Currency.get_user_currencies(ctx, ctx.author.id)
            self._user_currencies[ctx.author.id] = currencies

        return currencies
