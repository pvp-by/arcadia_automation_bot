from discord import ButtonStyle, Interaction, Message
from discord.ui import View, Button, Select


class BaseView(View):
    assigned_message = None

    def __init__(self):
        super().__init__()

    def result(self):
        ...

    async def on_timeout(self) -> None:
        if self.assigned_message:
            await self.assigned_message.delete()

    def assign_message(self, message: Message):
        self.assigned_message = message


class TimedView(BaseView):
    async def on_timeout(self) -> None:
        if self.assigned_message:
            await self.assigned_message.edit(
                content=self.assigned_message.content,
                embed=self.assigned_message.embeds[0] if self.assigned_message.embeds else None,
                view=None
            )
