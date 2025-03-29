from typing import TYPE_CHECKING

from discord import Message
from discord.ext import commands

if TYPE_CHECKING:
    from main import App


class Context(commands.Context):
    @property
    def bot(self) -> "App":
        return super().bot

    @classmethod
    def is_sudo(cls, message: Message | None) -> bool:
        return not message or message.content.lower().startswith("sudo")
