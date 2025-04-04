from typing import List

import discord
from asyncpg import Pool
from discord import app_commands


async def currency_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    pattern = f"%{current}%"
    pool: Pool = getattr(interaction.client, "pool")
    async with pool.acquire() as con:
        records = await con.fetch(
            "SELECT id, name FROM currencies WHERE name ILIKE $1 OR icon ILIKE $2 LIMIT 25;",
            pattern,
            current,
        )

        return [
            app_commands.Choice(name=record["name"], value=str(record["id"]))
            for record in records
        ]
