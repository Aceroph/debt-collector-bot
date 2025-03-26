import functools
import json
from typing import Any, List

import discord
from asyncpg import Pool, Record
from discord.ext import commands

from utils.context import Context
from utils.errors import (
    CurrencyNotFoundError,
    NoCurrenciesError,
    TooManyCurrenciesError,
)


class Currency:
    def __init__(self, record: Record) -> None:
        self._id = record["id"]
        self._name = record["name"]
        self._icon = record["icon"]
        self._owner = record["owner"]
        self._hidden = record["hidden"]
        self._created_at = record["created_at"]
        self._allowed_roles = record["allowed_roles"]

    @property
    def info_short(self) -> str:
        return f"`{self.icon}` {self.name} - ID {self.id}"

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


class Account:
    def __init__(self, record: Record) -> None:
        self._wallet: float = record["wallet"]
        self._bank: float = record["bank"]


class AddCurrencyButton(discord.ui.Button):
    def __init__(self, currency_id: int, pool: Pool, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._currency_id = currency_id
        self._pool = pool

    async def callback(self, interaction: discord.Interaction) -> Any:
        match self.label:
            case "Yes":
                await add_currency(
                    self._pool,
                    interaction,
                    self._currency_id,
                )
            case _:
                await interaction.delete_original_response()


class DeleteCurrencyButton(discord.ui.Button):
    def __init__(self, currency_id: int, pool: Pool, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._currency_id = currency_id
        self._pool = pool

    async def callback(self, interaction: discord.Interaction) -> Any:
        match self.label:
            case "DELETE":
                # PURGE EVERYTHING
                async with self._pool.acquire() as con:
                    await con.execute(
                        """DELETE FROM currencies WHERE id = $1;
                           DELETE FROM banks WHERE currencyid = $1;
                           DELETE FROM transactions WHERE currencyid = $1;
                           UPDATE guildconfigs SET config = jsonb_set(
                              config::jsonb, '{"currencies"}',
                              (config->'currencies')::jsonb - '[$1]'::jsonb)
                          WHERE config->'currencies' @> '[$1]';""",
                        self._currency_id,
                    )
                await interaction.delete_original_response()
            case _:
                await interaction.delete_original_response()


def has_economical_permission(permission: str):
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            ctx: Context = kwargs["ctx"]
            match permission:
                case "manage_currencies":
                    assert ctx.guild
                    if not (ctx.sudo or ctx.guild.owner_id == ctx.author.id):
                        raise commands.MissingPermissions(["manage_currencies"])

            return await func(*args, **kwargs)

        return wrapped

    return wrapper


async def get_guild_config(
    pool: Pool, guild: discord.Guild | int
) -> dict[str, int | str | bool]:
    if isinstance(guild, discord.Guild):
        guild = guild.id

    async with pool.acquire() as con:
        config = await con.fetchval(
            "SELECT config FROM guildconfigs WHERE guildid = $1;", guild
        )
        # If config for guild does not exist, create one
        if not config:
            await con.execute("INSERT INTO guildconfigs (guildid) VALUES ($1);", guild)
            config = await con.fetchval(
                "SELECT config FROM guildconfigs WHERE guildid = $1;", guild
            )
        return json.loads(config)


async def get_accounts(pool: Pool, member: discord.Member) -> List[Account]:
    async with pool.acquire() as con:
        currencies = await get_currency_ids(pool, member.guild.id)
        records = await con.fetch(
            "SELECT wallet, bank FROM banks WHERE userId = $1 AND currencyId = any($2::bigint[]);",
            member.id,
            currencies,
        )
        return [Account(r) for r in records]


async def get_currency_ids(pool: Pool, guild_id: discord.Guild | int) -> List[int]:
    guild_id = guild_id.id if isinstance(guild_id, discord.Guild) else guild_id
    async with pool.acquire() as con:
        config = await get_guild_config(pool, guild_id)
        records = await con.fetch(
            "SELECT id FROM currencies WHERE id = any($1::bigint[]);",
            config.get("currencies", []),
        )
        if len(records) == 0:
            raise NoCurrenciesError

        return [r["id"] for r in records]


async def get_currencies(pool: Pool, guild_id: discord.Guild | int) -> List[Currency]:
    guild_id = guild_id.id if isinstance(guild_id, discord.Guild) else guild_id
    async with pool.acquire() as con:
        config = await get_guild_config(pool, guild_id)
        records = await con.fetch(
            "SELECT * FROM currencies WHERE id = any($1::integer[]);",
            config["currencies"],
        )
        if len(records) == 0:
            raise NoCurrenciesError

        return [Currency(r) for r in records]


async def get_currency(pool: Pool, id: int) -> Currency:
    async with pool.acquire() as con:
        record = await con.fetchrow("SELECT * FROM currencies WHERE id = $1;", id)
        if not record:
            raise CurrencyNotFoundError
        return Currency(record)


async def add_currency(
    pool: Pool,
    ctx: Context | discord.Interaction,
    currency: Currency | int,
    bypass: bool = False,
) -> None:
    assert ctx.guild
    currency = (
        currency
        if isinstance(currency, Currency)
        else await get_currency(pool, currency)
    )

    if not bypass:
        try:
            currencies = await get_currencies(pool, ctx.guild)
            if len(currencies) == 5:
                raise TooManyCurrenciesError
        except NoCurrenciesError:
            pass

    async with pool.acquire() as con:
        await con.execute(
            """UPDATE guildconfigs
                          SET config = jsonb_set(
                              config::jsonb, '{"currencies"}',
                              (config->'currencies')::jsonb || '[$1]'::jsonb)
                          WHERE guildid = $2;""",
            currency.id,
        )

    embed = discord.Embed(
        title="Added currency to guild",
        description=f"> [+] ({currency.icon}) {currency.name}",
        color=discord.Color.gold(),
    )
    if isinstance(ctx, commands.Context):
        await ctx.reply(embed=embed, mention_author=False)
    else:
        await ctx.response.edit_message(embed=embed, view=None)


async def remove_currency(
    pool: Pool,
    ctx: Context | discord.Interaction,
    currency: Currency | int,
) -> None:
    assert ctx.guild
    currency = (
        currency
        if isinstance(currency, Currency)
        else await get_currency(pool, currency)
    )

    try:
        currencies = await get_currency_ids(pool, ctx.guild)
        if not currency.id in currencies:
            raise NoCurrenciesError
    except NoCurrenciesError:
        pass

    async with pool.acquire() as con:
        await con.execute(
            """UPDATE guildconfigs
                          SET config = jsonb_set(
                              config::jsonb, '{"currencies"}',
                              (config->'currencies')::jsonb - '[$1]'::jsonb)
                          WHERE guildid = $2;""",
            currency.id,
        )

    embed = discord.Embed(
        title="Removed currency to guild",
        description=f"> [-] ({currency.icon}) {currency.name}",
        color=discord.Color.gold(),
    )
    if isinstance(ctx, commands.Context):
        await ctx.reply(embed=embed, mention_author=False)
    else:
        await ctx.response.edit_message(embed=embed, view=None)
