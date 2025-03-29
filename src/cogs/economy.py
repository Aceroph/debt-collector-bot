import asyncio
import datetime
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from services.account import Account
from services.config import Config
from services.currency import Currency
from utils.context import Context
from utils.converters import CurrencyConverter
from utils.errors import CurrencyNotFoundError, NoCurrenciesError
from views.currency_management import AddCurrencyView, DeleteCurrencyView

if TYPE_CHECKING:
    from main import App


class Economy(commands.Cog):
    @commands.guild_only()
    @commands.hybrid_command(aliases=["bal", "money"])
    @discord.app_commands.describe(
        member="The one you're trying to spy on.", currency="The currency to show only."
    )
    async def balance(
        self,
        ctx: Context,
        member: discord.Member | None = None,
        currency: CurrencyConverter = None,
    ) -> None:
        """Returns your balance."""
        assert isinstance(ctx.author, discord.Member)
        member = member or ctx.author
        if currency:
            accounts = {currency.id: await Account.get(ctx, member, currency)}
        else:
            accounts = await Account.get_all(ctx, member)

        description = ""
        for currency_id, account in accounts.items():
            currency = await Currency.get(ctx, currency_id)
            description += currency.name + "s\n"
            description += f"> {account.wallet:,} {currency.icon}\n\n"

        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s balance{'' if currency else 's'}",
            description=description,
            color=member.accent_color,
            timestamp=datetime.datetime.now(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        await ctx.reply(embed=embed, mention_author=False)

    @commands.guild_only()
    @commands.hybrid_group(aliases=["currency"], fallback="list")
    async def currencies(self, ctx: Context) -> None:
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
            color=discord.Color.gold(),
        )

        await ctx.reply(embed=embed, mention_author=False)

    @currencies.command("create")
    @discord.app_commands.describe(
        name="The name of your currency.", icon="The icon for your currency."
    )
    async def currencies_create(
        self, ctx: Context, *, name: str, icon: str = ""
    ) -> None:
        """Creates a new currency to be later added to a server."""
        currency = None
        async with ctx.bot.pool.acquire() as con:
            currency = Currency(
                await con.fetchrow(
                    "INSERT INTO currencies (name, icon, owner) VALUES ($1, $2, $3) RETURNING *;",
                    name,
                    icon,
                    ctx.author.id,
                )
            )

        embed = discord.Embed(
            title="Created currency",
            description=f"> ({icon}) {name}",
            color=discord.Color.gold(),
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
    async def currency_delete(self, ctx: Context, currency: int) -> None:
        """Deletes a currency you created."""
        async with ctx.bot.pool.acquire() as con:
            record = await con.fetchrow(
                "SELECT * FROM currencies WHERE id = $1;", currency
            )
            accounts = await con.fetchval(
                "SELECT COUNT(*) FROM banks WHERE currencyid = $1;", currency
            )
            if not record:
                raise CurrencyNotFoundError
            currency_obj = Currency(record)
            if not (
                currency_obj.owner_id == ctx.author.id or Context.is_sudo(ctx.message)
            ):
                raise commands.NotOwner

            embed = discord.Embed(
                title="Warning",
                description=(
                    ">>> Are you sure you want to do this ?\n"
                    f"{accounts} accounts are going to get deleted."
                ),
                color=discord.Color.red(),
            )
            assert isinstance(ctx.author, discord.Member)
            await ctx.reply(
                embed=embed,
                view=DeleteCurrencyView(ctx, currency_obj),
                mention_author=False,
            )

    @Config.has_permission("manage_currencies")
    @currencies.command("add")
    @discord.app_commands.describe(currency="The ID of the currency to add.")
    async def currencies_add(self, ctx: Context, currency: int) -> None:
        """Adds an existing currency to the current server, with a limit of 5."""
        config = await Config.get(ctx)
        await config.add_currency(currency)

    @Config.has_permission("manage_currencies")
    @currencies.command("remove")
    @discord.app_commands.describe(currency="The ID of the currency to remove.")
    async def currencies_remove(self, ctx: Context, currency: int) -> None:
        """Removes an existing currency to the current server."""
        config = await Config.get(ctx)
        await config.remove_currency(currency)

    @currencies.command("search")
    @discord.app_commands.describe(query="Your searching query.")
    async def currencies_search(
        self, ctx: Context, *, query: str | None = None
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
            description = "\n".join([str(Currency(c)) for c in currencies])

        embed = discord.Embed(
            title="\N{RIGHT-POINTING MAGNIFYING GLASS} The Money Finder",
            description=description,
            color=discord.Color.gold(),
        )

        await ctx.reply(embed=embed, mention_author=False)

    @currencies.command("info")
    @discord.app_commands.describe(currency="The currency to look into.")
    async def currencies_info(self, ctx: Context, currency: int) -> None:
        """Salvages info on currencies"""
        users = 0
        guilds = 0
        currency_obj = None
        async with ctx.bot.pool.acquire() as con:
            record = await con.fetchrow(
                "SELECT * FROM currencies WHERE id = $1;", currency
            )
            if not record:
                raise CurrencyNotFoundError

            currency_obj = Currency(record)
            if currency_obj.hidden and not (
                ctx.author.id == currency_obj.owner_id or Context.is_sudo(ctx.message)
            ):
                raise CurrencyNotFoundError

            users = await con.fetchval(
                "SELECT COUNT(*) FROM currencies WHERE id = $1;", currency_obj.id
            )
            guilds = await con.fetchval(
                """SELECT COUNT(*) FROM guildconfigs WHERE currencies @> $1;""",
                [currency_obj.id],
            )

        embed = discord.Embed(
            title=(
                f"{currency_obj.icon} - {currency_obj.name}"
                if currency_obj.icon != ""
                else currency_obj.name
            ),
            description=(
                f">>> Owned by {currency_obj.owner_mention}\n"
                f"Used by {users} users and {guilds} servers\n"
                f"Created {currency_obj.created_at}\n"
            ),
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"ID: {currency_obj.id}")
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: "App") -> None:
    await bot.add_cog(Economy())
