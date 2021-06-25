from discord import ButtonStyle, Interaction
from discord.ui import Button, button


from ..github_integration import *
from ..cogs.cog_util import MultiSelectionView
from ..cogs.embeds import *

from .base_view import TimedView, BaseView


class IssueControls(TimedView):
    def __init__(self, session, repo: str, github_id: int):
        self.session = session
        self.repo = repo
        self.github_id = github_id
        super().__init__()

    @button(label="Add labels", style=ButtonStyle.green)
    async def add_labels_action(self, _button: Button, interaction: Interaction):
        status, data = await get_repo_labels(self.session, self.repo)
        if not status:
            return
        repo_labels = [label["name"] for label in data]
        selection_view = MultiSelectionView(repo_labels[:24])

        async def finish_callback(selection: List[str]):
            await add_labels(self.session, self.repo, self.github_id, selection)

        selection_view.on_finish(finish_callback)

        msg = await interaction.channel.send(f"{interaction.user.mention}, select labels:", view=selection_view)
        selection_view.assign_message(msg)

    @button(label="Assign", style=ButtonStyle.blurple)
    async def assign_action(self, _button: Button, interaction: Interaction):
        status, data = await get_arcadia_team_members(self.session)
        if not status:
            return
        members = [member["login"] for member in data]
        selection_view = MultiSelectionView(members[:24])

        async def finish_callback(selection: List[str]):
            await assign_issue(self.session, self.repo, self.github_id, selection)

        selection_view.on_finish(finish_callback)

        msg = await interaction.channel.send(f"{interaction.user.mention}, select users:", view=selection_view)
        selection_view.assign_message(msg)

    @button(label="Close issue", style=ButtonStyle.red, row=1)
    async def close_issue_action(self, _button: Button, interaction: Interaction):
        await close_issue(self.session, self.repo, self.github_id)

    @button(emoji="❎", style=ButtonStyle.danger)
    async def remove_embed(self, _button: Button, interaction: Interaction):
        await interaction.message.delete()
        self.assigned_message = None


class PullRequestControls(IssueControls):
    def __init__(self, session, repo: str, pr_id: int, pr_data: dict):
        super().__init__(session, repo, pr_id)
        button_text, mergeable = get_pr_merge_state(pr_data)
        self.add_item(Button(label=button_text, style=ButtonStyle.blurple, disabled=not mergeable, row=1))

