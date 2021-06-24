from discord import Game, Embed, ButtonStyle, Interaction
from discord.ui import View, Button, button, select


class Controls(View):
    @button()
    async def action(self):
        pass