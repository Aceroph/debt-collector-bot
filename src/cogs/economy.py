import datetime
from typing import TYPE_CHECKING, Optional

import discord
from discord import Member, User, app_commands
from discord.ext import commands

from services import Account, Config, Currency
from services.currency import CurrencyWithAmount
from utils import get_accent_color
from utils.completions import currency_with_amount, guild_currencies
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
        *,
        currency: Currency | None = None,
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

    @commands.hybrid_command(name="update")
    @app_commands.autocomplete(currency=currency_with_amount)
    @app_commands.rename(currency="amount")
    @app_commands.describe(
        currency="The amount of currency changed.",
        user="The user to update, defaults to yourself.",
    )
    @Config.has_permission("banker")
    async def update_account(
        self,
        ctx: commands.Context["DebtBot"],
        *,
        currency: CurrencyWithAmount,
        user: Optional[Member | User] = None,
    ) -> None:
        """Adds money to an account, super legit."""
        _user = user or ctx.author
        assert isinstance(currency, Currency)
        account = await Account.get(ctx, _user, currency)
        old_money = account.wallet
        await account.add_money(
            currency.amount, True, "printed" if currency.amount > 0 else "burned"
        )

        embed = discord.Embed(
            title="Printed money" if currency.amount > 0 else "Burned money",
            description=f"> {old_money:,} → {account.wallet:,} {currency.icon}",
            color=get_accent_color(_user),
            timestamp=datetime.datetime.now(),
        )
        embed.set_thumbnail(url=_user.display_avatar.url)

        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command()
    @app_commands.autocomplete(currency=currency_with_amount)
    @app_commands.rename(currency="amount")
    @app_commands.describe(
        currency="The amount of to spend.",
    )
    async def spend(
        self, ctx: commands.Context["DebtBot"], *, currency: CurrencyWithAmount
    ) -> None:
        """Spends money, if you have it."""
        assert isinstance(currency, Currency)
        account = await Account.get(ctx, ctx.author, currency)
        old_money = account.wallet
        if abs(currency.amount) > old_money:
            raise NotEnoughMoneyError(old_money - currency.amount, currency.icon)

        await account.add_money(-abs(currency.amount), True, reason="spent")

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
