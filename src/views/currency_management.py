import discord

from services.config import Config
from services.currency import Currency
from utils.context import Context


class ManageCurrencyView(discord.ui.View):
    def __init__(self, ctx: Context, currency: Currency) -> None:
        super().__init__(timeout=40)
        self._ctx = ctx
        self._currency = currency

    @property
    def currency(self) -> Currency:
        return self._currency


class AddCurrencyView(ManageCurrencyView):
    def __init__(self, ctx: Context, currency: Currency):
        super().__init__(ctx, currency)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    @Config.has_permission("manage_currencies")
    async def yes(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        config = await Config.get(self._ctx)
        await config.add_currency(self._currency)

        if interaction.message:
            await interaction.message.delete()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    @Config.has_permission("manage_currencies")
    async def no(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.message:
            await interaction.message.delete()


class DeleteCurrencyView(ManageCurrencyView):
    def __init__(self, ctx: Context, currency: Currency):
        super().__init__(ctx, currency)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.red)
    @Config.has_permission("manage_currencies")
    async def delete(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        async with self._ctx.bot.pool.acquire() as con:
            await con.execute("DELETE FROM currencies WHERE id = $1;", self.currency.id)
            await con.execute(
                "DELETE FROM banks WHERE currencyid = $1;", self.currency.id
            )
            await con.execute(
                "DELETE FROM transactions WHERE currencyid = $1;", self.currency.id
            )
            await con.execute(
                "UPDATE guildconfigs SET currencies = array_remove(currencies, $1);",
                self.currency.id,
            )
        if interaction.message:
            await interaction.message.delete()

    @discord.ui.button(label="No", style=discord.ButtonStyle.gray)
    @Config.has_permission("manage_currencies")
    async def no(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.message:
            await interaction.message.delete()
