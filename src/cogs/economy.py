import datetime
from typing import TYPE_CHECKING, Optional

import discord
from discord import Member, User, app_commands
from discord.ext import commands

from services import Account, Config, Currency
from utils import CurrencyConverter, get_accent_color
from utils.completions import guild_currencies
from utils.errors import NotEnoughMoneyError

if TYPE_CHECKING:
    from main import DebtBot


class Economy(commands.Cog):
    @commands.hybrid_command(aliases=["bal", "money"])
    @app_commands.autocomplete(currency=guild_currencies)
    @app_commands.describe(
        user="The one you're trying to spy on.", currency="The currency to show only."
    )
    async def balance(
        self,
        ctx: commands.Context["DebtBot"],
        user: Optional[Member | User] = None,
        currency: CurrencyConverter | None = None,
    ) -> None:
        """Returns your balance."""
        _user = user or ctx.author
        if currency:
            assert isinstance(currency, Currency)
            accounts = {currency.id: await Account.get(ctx, _user, currency)}
        else:
            accounts = await Account.get_all(ctx, _user)

        description = ""
        for currency_id, account in accounts.items():
            c = await Currency.get(ctx, currency_id)
            description += (
                f"# {c.name}{'' if c.name.endswith('s') else 's'}\n"
                f"## <:curved_line:1355629405925413044> {account.wallet:,} {c.icon}\n\n"
            )

        embed = discord.Embed(
            title=f"{_user.display_name}'s balance{'' if currency else 's'}",
            description=description,
            color=get_accent_color(_user),
            timestamp=datetime.datetime.now(),
        )
        embed.set_thumbnail(url=_user.display_avatar.url)

        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="update", aliases=["add", "remove"])
    @app_commands.autocomplete(currency=guild_currencies)
    @app_commands.describe(
        amount="The amount of money to add/remove.",
        currency="The currency affected.",
        user="The user to update, defaults to yourself.",
    )
    @Config.has_permission("banker")
    async def update_account(
        self,
        ctx: commands.Context["DebtBot"],
        amount: int,
        currency: CurrencyConverter,
        user: Optional[Member | User] = None,
    ) -> None:
        """Adds money to an account, super legit."""
        _user = user or ctx.author
        assert isinstance(currency, Currency)
        account = await Account.get(ctx, _user, currency)
        old_money = account.wallet
        await account.add_money(amount, True, "printed" if amount > 0 else "burned")

        embed = discord.Embed(
            title="Printed money" if amount > 0 else "Burned money",
            description=f"> {old_money:,} → {account.wallet:,} {currency.icon}",
            color=get_accent_color(_user),
            timestamp=datetime.datetime.now(),
        )
        embed.set_thumbnail(url=_user.display_avatar.url)

        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command()
    @app_commands.autocomplete(currency=guild_currencies)
    @app_commands.describe(
        amount="The amount of money to spend.",
        currency="The currency to spend.",
    )
    async def spend(
        self, ctx: commands.Context["DebtBot"], amount: int, currency: CurrencyConverter
    ) -> None:
        """Spends money, if you have it."""
        assert isinstance(currency, Currency)
        account = await Account.get(ctx, ctx.author, currency)
        old_money = account.wallet
        if abs(amount) > old_money:
            raise NotEnoughMoneyError(old_money - amount, currency.icon)

        await account.add_money(-abs(amount), True, reason="spent")

        embed = discord.Embed(
            title="Spent money",
            description=f"> {old_money:,}  → {account.wallet:,} {currency.icon}",
            color=get_accent_color(ctx.author),
            timestamp=datetime.datetime.now(),
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: "DebtBot") -> None:
    await bot.add_cog(Economy())
