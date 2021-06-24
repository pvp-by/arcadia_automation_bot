from discord import Game, Embed, ButtonStyle, Interaction
from discord.ui import View, Button, button, select

try:
    from ..github_integration import *
    from ..cogs.cog_util import get_multi_selection_standalone, MultiSelectionView
except ValueError:
    from github_integration import *
    from cogs.cog_util import get_multi_selection_standalone, MultiSelectionView


class IssueControls(View):
    message = None

    def __init__(self, session, repo: str, issue_id: int):
        self.session = session
        self.repo = repo
        self.issue_id = issue_id
        super().__init__()

    @button(label="Add labels", style=ButtonStyle.green)
    async def add_labels_action(self, _button: Button, interaction: Interaction):
        status, data = await get_repo_labels(self.session, self.repo)
        if not status:
            return
        repo_labels = [label["name"] for label in data]
        selection_view = MultiSelectionView(repo_labels[:24])

        async def finish_callback(selection: List[str]):
            await add_labels(self.session, self.repo, self.issue_id, selection)

        selection_view.on_finish(finish_callback)

        await interaction.channel.send(f"{interaction.user.mention}, select labels:", view=selection_view)

    @button(label="Assign", style=ButtonStyle.blurple)
    async def assign_action(self, _button: Button, interaction: Interaction):
        status, data = await get_arcadia_team_members(self.session)
        if not status:
            return
        members = [member["login"] for member in data]
        selection_view = MultiSelectionView(members[:24])

        async def finish_callback(selection: List[str]):
            await assign_issue(self.session, self.repo, self.issue_id, selection)

        selection_view.on_finish(finish_callback)

        await interaction.channel.send(f"{interaction.user.mention}, select users:", view=selection_view)

    @button(label="Close", style=ButtonStyle.red)
    async def close_issue_action(self, _button: Button, interaction: Interaction):
        await close_issue(self.session, self.repo, self.issue_id)

    def assign_message(self, message):
        self.message = message

    async def on_timeout(self) -> None:
        if self.message:
            self.message.edit(content=self.message.content, embeds=self.message.embeds, view=None)
