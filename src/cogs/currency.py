import asyncio
import datetime
from typing import TYPE_CHECKING

import discord
import regex
from discord.ext import commands

from services import Config, Currency
from utils import CurrencyConverter, currency_autocomplete, get_accent_color, is_sudo
from utils.errors import NoCurrenciesError
from views.currency_management import AddCurrencyView, DeleteCurrencyView

if TYPE_CHECKING:
    from main import DebtBot


class CurrencyCog(commands.Cog):
    @commands.guild_only()
    @commands.hybrid_group(aliases=["currency"], fallback="list")
    async def currencies(self, ctx: commands.Context["DebtBot"]) -> None:
        """Lists the currencies of this server."""
        assert ctx.guild
        config = await Config.get(ctx)

        if len(config.currencies) == 0:
            raise NoCurrenciesError

        description = "\n".join(
            [str(await Currency.get(ctx, id)) for id in config.currencies]
        )
        embed = discord.Embed(
            title="Currencies in this server",
            description=description,
            color=get_accent_color(ctx.author),
            timestamp=datetime.datetime.now(),
        )
        embed.set_footer(text=f"{len(config.currencies)}/{config.max_currencies}")

        await ctx.reply(embed=embed, mention_author=False)

    @currencies.command("create")
    @discord.app_commands.describe(
        name="The name of your currency.", icon="The icon for your currency."
    )
    async def currencies_create(
        self, ctx: commands.Context["DebtBot"], name: str, icon: str
    ) -> None:
        """Creates a new currency to be later added to a server."""
        # Check if icon is valid
        if not regex.match(r"<a?:.+?:\d{18}>|.{1,4}", icon):
            raise commands.BadArgument("Invalid icon for currency")

        currency = None
        async with ctx.bot.pool.acquire() as con:
            currency = Currency(
                ctx,
                await con.fetchrow(
                    "INSERT INTO currencies (name, icon, owner) VALUES ($1, $2, $3) RETURNING *;",
                    name,
                    icon,
                    ctx.author.id,
                ),
            )

        embed = discord.Embed(
            title="Created currency",
            description=f"> {currency}",
            color=get_accent_color(ctx.author),
        )
        await ctx.reply(embed=embed, mention_author=False)

        await asyncio.sleep(1)

        assert isinstance(ctx.author, discord.Member)
        await ctx.send(
            "Would you like to add this currency to the current guild?",
            view=AddCurrencyView(ctx, currency),
        )

    @currencies.command("delete")
    @discord.app_commands.describe(currency="The ID of the currency to delete.")
    async def currency_delete(self, ctx: commands.Context["DebtBot"], currency: CurrencyConverter("owned")) -> None:  # type: ignore
        """Deletes a currency you created."""
        assert isinstance(currency, Currency)
        if not (currency.owner_id == ctx.author.id or is_sudo(ctx)):
            raise commands.NotOwner

        uses = await currency.get_uses()

        embed = discord.Embed(
            title="Warning",
            description=(
                ">>> Are you sure you want to do this ?\n"
                f"{uses} accounts are going to get deleted."
            ),
            color=get_accent_color(ctx.author),
        )
        assert isinstance(ctx.author, discord.Member)
        await ctx.reply(
            embed=embed,
            view=DeleteCurrencyView(ctx, currency),
            mention_author=False,
        )

    @Config.has_permission("manage_currencies")
    @currencies.command("add")
    @discord.app_commands.describe(currency="The ID of the currency to add.")
    async def currencies_add(
        self, ctx: commands.Context["DebtBot"], currency: CurrencyConverter
    ) -> None:
        """Adds an existing currency to the current server, with a limit of 5."""
        config = await Config.get(ctx)
        assert isinstance(currency, Currency)
        await config.add_currency(currency)

    @Config.has_permission("manage_currencies")
    @currencies.command("remove")
    @discord.app_commands.autocomplete(currency=currency_autocomplete)
    @discord.app_commands.describe(currency="The ID of the currency to remove.")
    async def currencies_remove(
        self, ctx: commands.Context["DebtBot"], currency: CurrencyConverter("guild")  # type: ignore
    ) -> None:
        """Removes an existing currency to the current server."""
        config = await Config.get(ctx)
        assert isinstance(currency, Currency)
        await config.remove_currency(currency)

    @currencies.command("search")
    @discord.app_commands.describe(query="Your searching query.")
    async def currencies_search(
        self, ctx: commands.Context["DebtBot"], *, query: str | None = None
    ) -> None:
        """Searches currencies based on their name"""
        async with ctx.bot.pool.acquire() as con:
            if query:
                pattern = "%" + query + "%"
                currencies = await con.fetch(
                    "SELECT * FROM currencies WHERE name ILIKE $1 OR icon ILIKE $1 LIMIT 10;",
                    pattern,
                )
            else:
                currencies = await con.fetch("SELECT * FROM currencies LIMIT 10;")

        if len(currencies) == 0:
            description = "Nothing found."
        else:
            description = "\n".join([str(Currency(ctx, c)) for c in currencies])

        embed = discord.Embed(
            title="\N{RIGHT-POINTING MAGNIFYING GLASS} The Money Finder",
            description=description,
            color=get_accent_color(ctx.author),
        )

        await ctx.reply(embed=embed, mention_author=False)

    @currencies.command("info")
    @discord.app_commands.describe(currency="The currency to look into.")
    async def currencies_info(
        self, ctx: commands.Context["DebtBot"], currency: CurrencyConverter
    ) -> None:
        """Salvages info on currencies"""
        assert isinstance(currency, Currency)
        uses = await currency.get_uses()

        embed = discord.Embed(
            title=(
                f"{currency.icon} - {currency.name}"
                if currency.icon != ""
                else currency.name
            ),
            description=(
                f">>> Owned by {currency.owner_mention}\n"
                f"Used by {uses} users\n"
                f"Created {currency.created_at}\n"
            ),
            color=get_accent_color(ctx.author),
        )
        embed.set_footer(text=f"ID: {currency.id}")
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: "DebtBot") -> None:
    await bot.add_cog(CurrencyCog())
