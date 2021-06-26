from discord import ButtonStyle, Interaction
from discord.ui import View, Button, Select
from discord.components import SelectOption
from typing import List, Optional

from .base_view import BaseView


class DropdownSelect(Select):
    def __init__(self, options: List[str]):
        select_options = [
            SelectOption(label=option) for i, option in enumerate(options)
        ]

        super().__init__(options=select_options, max_values=len(select_options))
        print("select init")

    async def callback(self, interaction: Interaction):
        print(interaction.response)
        print(interaction.data)
        self.view.stop()


class DropdownView(View):
    def __init__(self, options: List[str]):
        super().__init__()
        self.add_item(DropdownSelect(options))
        print("dropdown select")

    def result(self):
        return "none?"


class SelectionButton(Button):
    option = None

    def __init__(self, option: str, style: ButtonStyle):
        super().__init__(label=option, style=style)
        self.option = option

    async def callback(self, interaction: Interaction):
        self.view.selected_item = self.option
        self.view.stop()
        await interaction.message.delete()


class SelectionView(BaseView):
    selected_item = None

    def __init__(self, options: List[str]):
        super().__init__()

        for option in options:
            self.add_item(SelectionButton(option, ButtonStyle.primary))

    def result(self):
        return self.selected_item


class MultiSelectionButton(Button):
    option = None
    finishing_button = False

    def __init__(self, option: str, finishing_button: bool = False, **kwargs):
        super().__init__(label=option, **kwargs)
        self.option = option
        self.finishing_button = finishing_button

    async def callback(self, interaction: Interaction):
        if self.finishing_button:
            await self.view.finish()
            await interaction.message.delete()
            return
        if self.option not in self.view.selected_items:
            self.view.selected_items.append(self.option)
            self.style = ButtonStyle.danger
        else:
            self.style = ButtonStyle.primary
            self.view.selected_items.remove(self.option)
            if len(self.view.selected_items) == 0:
                self.style = ButtonStyle.primary
        content = f"Selected: {', '.join(self.view.selected_items)}"
        if '\n' in interaction.message.content:
            mention_part = interaction.message.content.split('\n')[0]
            content = f"{mention_part}\n{content}"
        else:
            content = f"{interaction.message.content}\n{content}"

        await interaction.response.edit_message(
            content=content,
            view=self.view
        )


class MultiSelectionView(BaseView):
    selected_items = None
    finish_callback = None

    def __init__(self, options: List[str], selected_options: Optional[List[str]] = None):
        super().__init__()
        self.selected_items = selected_options if selected_options else []

        for option in options:
            button_style = ButtonStyle.danger if option in self.selected_items else ButtonStyle.primary
            self.add_item(MultiSelectionButton(option, style=button_style))
        self.apply_button = MultiSelectionButton(
            "Apply", style=ButtonStyle.success, finishing_button=True, row=4
        )
        self.add_item(self.apply_button)

    def on_finish(self, callback):
        self.finish_callback = callback

    async def finish(self):
        if self.finish_callback:
            await self.finish_callback(self.selected_items)
        self.stop()


