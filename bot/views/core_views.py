from discord import Game, Embed, ButtonStyle, Interaction
from discord.ui import View, Button, button, select
from typing import Dict


class Controls(View):
    @button()
    async def action(self):
        pass


class FeedbackControls(View):
    def __init__(self, links: Dict[int, str]):
        super().__init__()
        for amount, link in links.items():
            self.add_item(
                Button(emoji="<:fortune:831077783446749194>", label=str(amount), url=link, style=ButtonStyle.primary)
            )
