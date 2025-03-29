from typing import TYPE_CHECKING

from discord import Color, Member, Message, User
from discord.ext import commands

if TYPE_CHECKING:
    from main import App


class Context(commands.Context):
    @property
    def bot(self) -> "App":
        return super().bot

    @classmethod
    def is_sudo(cls, message: Message | None) -> bool:
        return message != None and message.content.lower().startswith("sudo")

    @classmethod
    def color(cls, user: Member | User) -> Color:
        return (
            user.top_role.color
            if isinstance(user, Member)
            else Color.from_rgb(255, 255, 255)
        )
