import asyncio
from typing import TYPE_CHECKING

import discord
from discord import Member, mentions
from discord.ext import commands

from utils import database as db
from utils.context import Context
from utils.errors import CurrencyNotFoundError

if TYPE_CHECKING:
    from main import App


class Economy(commands.Cog):
    def __init__(self, bot: "App") -> None:
        self.bot = bot

    @commands.guild_only()
    @commands.hybrid_command()
    async def balance(self, ctx: Context, member: discord.Member | None = None) -> None:
        """Returns your balance."""
        assert isinstance(ctx.author, Member)
        member = member or ctx.author
        accounts = await db.get_accounts(self.bot.pool, member)
        await ctx.reply(f"{len(accounts)} accounts")

    @commands.guild_only()
    @commands.hybrid_group(aliases=["currency"], fallback="list")
    async def currencies(self, ctx: Context) -> None:
        """Lists the currencies of this server."""
        assert ctx.guild
        currencies = await db.get_currencies(self.bot.pool, ctx.guild)

        description = "\n".join([c.info_short for c in currencies])
        embed = discord.Embed(
            title="Currencies in this server",
            description=description,
            color=discord.Color.gold(),
        )

        await ctx.reply(embed=embed, mention_author=False)

    @currencies.command("create")
    async def currencies_create(
        self, ctx: Context, icon: str = "$", *, name: str
    ) -> None:
        """Creates a new currency to be later added to a server."""
        currency = None
        async with self.bot.pool.acquire() as con:
            currency = db.Currency(
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

        button_yes = db.AddCurrencyButton(
            currency,
            self.bot.pool,
            style=discord.ButtonStyle.green,
            label="Yes",
            custom_id=f"currency_add:{currency.id}",
        )
        button_no = db.AddCurrencyButton(
            currency, self.bot.pool, style=discord.ButtonStyle.red, label="No"
        )
        view = discord.ui.View(timeout=40)
        view.add_item(button_yes)
        view.add_item(button_no)
        await ctx.send(
            "Would you like to add this currency to the current guild?", view=view
        )

    @currencies.command("delete")
    async def currency_delete(self, ctx: Context, currency_id: int) -> None:
        """Deletes a currency you created."""
        async with self.bot.pool.acquire() as con:
            record = await con.fetchrow(
                "SELECT * FROM currencies WHERE id = $1;", currency_id
            )
            accounts = await con.fetchval(
                "SELECT COUNT(*) FROM banks WHERE currencyid = $1;", currency_id
            )
            if not record:
                raise CurrencyNotFoundError
            currency = db.Currency(record)
            if not (ctx.sudo or currency.owner_id == ctx.author.id):
                raise commands.NotOwner

            embed = discord.Embed(
                title="Warning",
                description=(
                    ">>> Are you sure you want to do this ?"
                    f"{accounts} accounts are going to get deleted."
                ),
                color=discord.Color.red(),
            )
            button_yes = db.DeleteCurrencyButton(
                currency,
                self.bot.pool,
                style=discord.ButtonStyle.red,
                label="DELETE",
                custom_id=f"currency_add:{currency.id}",
            )
            button_no = db.DeleteCurrencyButton(
                currency, self.bot.pool, style=discord.ButtonStyle.gray, label="Cancel"
            )
            view = discord.ui.View(timeout=40)
            view.add_item(button_yes)
            view.add_item(button_no)
            await ctx.reply(embed=embed, view=view, mention_author=False)

    @db.has_economical_permission("manage_currencies")
    @currencies.command("add")
    async def currencies_add(self, ctx: Context, currency_id: int) -> None:
        """Adds an existing currency to the current server, with a limit of 5."""
        await db.add_currency(self.bot.pool, ctx, currency_id, ctx.sudo)

    @db.has_economical_permission("manage_currencies")
    @currencies.command("remove")
    async def currencies_remove(self, ctx: Context, currency_id: int) -> None:
        """Removes an existing currency to the current server."""
        await db.remove_currency(self.bot.pool, ctx, currency_id)

    @currencies.command("search")
    async def currencies_search(
        self, ctx: Context, *, query: str | None = None
    ) -> None:
        """Searches currencies based on their name"""
        async with self.bot.pool.acquire() as con:
            if query:
                pattern = "%" + query + "%"
                currencies = await con.fetch(
                    "SELECT * FROM currencies WHERE name ILIKE $1 OR icon ILIKE $1 LIMIT 10;",
                    pattern,
                )
            else:
                currencies = await con.fetch("SELECT * FROM currencies LIMIT 10;")

        description = "\n".join([f"({c['icon']}) {c['name']}" for c in currencies])
        embed = discord.Embed(
            title="Currencies matching query",
            description=description,
            color=discord.Color.gold(),
        )

        await ctx.reply(embed=embed, mention_author=False)

    @currencies.command("info")
    async def currencies_info(self, ctx: Context, currency_id: int) -> None:
        """Salvages info on currencies"""
        users = 0
        guilds = 0
        currency = None
        async with self.bot.pool.acquire() as con:
            record = await con.fetchrow(
                "SELECT * FROM currencies WHERE id = $1;", currency_id
            )
            if not record:
                raise CurrencyNotFoundError

            currency = db.Currency(record)
            if currency.hidden and not (ctx.author.id == currency.owner_id or ctx.sudo):
                raise CurrencyNotFoundError

            users = await con.fetchval(
                "SELECT COUNT(*) FROM currencies WHERE id = $1;", currency.id
            )
            guilds = await con.fetchval(
                """SELECT COUNT(*) FROM guildconfigs WHERE (config->'currencies')::jsonb @> $1::jsonb;""",
                str(currency.id),
            )

        embed = discord.Embed(
            title=f"{currency.icon} - {currency.name}",
            description=(
                f">>> Owned by {currency.owner_mention}\n"
                f"Used by {users} users and {guilds} servers\n"
                f"Created {currency.created_at}\n"
            ),
            color=discord.Color.gold(),
        )
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: "App") -> None:
    await bot.add_cog(Economy(bot))
