from discord.ext import commands


class Context(commands.Context):
    @property
    def sudo(self) -> bool:
        return self.message.content.lower().startswith("sudo")
