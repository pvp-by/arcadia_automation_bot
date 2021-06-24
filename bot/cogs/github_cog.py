from discord.ext import commands
from discord import colour, Member, Message
import asyncio
import re

# import nonsense cause of different root folders in docker and in IDE
try:
    from ..github_integration import *
    from ..views.github_views import *
    from cog_util import *
    from embeds import *
except ValueError:
    from github_integration import *
    from cogs.cog_util import *
    from cogs.embeds import *
    from views.github_views import *


class Github(commands.Cog, name="Github"):
    def __init__(self, bot):
        self.bot = bot
        self.command_list = [
            [["list", "l"], self._list_issues],
            [["close", "c"], self._close_issue],
            [["open", "o"], self._open_issue],
            [["edit", "e"], self._edit_issue],
            [["attach", "at"], self._attach_image],
            [["comment", "c"], self._comment_issue],
            [["search", "s"], self._search_issues],
            [["assign", "as"], self._assign_to_issue],
        ]
        self.private_repos = ["reVolt", "custom_hero_clash", "chclash_webserver", "war_masters"]

        self.repos_stringified_list = ""
        self.url_regex = re.compile(
            "(https?:\/\/(.+?\.)?github\.com\/arcadia-redux(\/[A-Za-z0-9\-\._~:\/\?#\[\]@!$&'\(\)\*\+,;\=]*)?)"
        )

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("[COG] Github is ready!")
        self.repos_stringified_list = await github_init(self.bot)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        await self.process_github_links(message)

        reference = message.reference
        if not reference:
            return

        if reference.cached_message:
            replied_message = reference.cached_message
        else:
            replied_message = await message.channel.fetch_message(reference.message_id)

        if replied_message.author != self.bot.user:
            return

        if not replied_message.embeds:
            return

        issue_link_split = replied_message.embeds[0].author.url.split("/")
        issue_id = issue_link_split[-1]
        repo = issue_link_split[-3]

        body = message.content
        lowered = body.lower()

        status = False

        if lowered.startswith("assign:"):
            assignees = body[7:].strip().split(" ")
            for i, assignee in enumerate(assignees):
                if assignee.startswith("<"):
                    assignees[i] = await self.bot.redis.hget(
                        "github_mention", assignee.replace("!", ""), encoding='utf8'
                    )
            status, _ = await assign_issue(self.bot.session, repo, issue_id, assignees)

        elif lowered.startswith("label:"):
            labels_base = body[6:].strip().split(" ")
            labels_final = []
            _reading_complex_label = False
            _complex_label = ""
            for m_label in labels_base:
                if m_label.startswith('"'):
                    _complex_label = m_label[1:]
                    _reading_complex_label = True
                    continue
                if m_label.endswith('"'):
                    _complex_label += f" {m_label[:-1]}"
                    _reading_complex_label = False
                    labels_final.append(_complex_label)
                    _complex_label = ""
                    continue
                if _reading_complex_label:
                    _complex_label += m_label
                else:
                    labels_final.append(m_label)
            status, _ = await add_labels(self.bot.session, repo, issue_id, labels_final)

        elif lowered.startswith("close:"):
            reason = body[7:].strip()
            status, _ = await comment_issue(self.bot.session, repo, issue_id, reason)
            status, _ = await close_issue(self.bot.session, repo, issue_id)

        else:
            if message.attachments:
                body += await process_attachments_contextless(
                    message, self.bot.session, message.attachments[0].url, False
                )

            status, _ = await comment_issue(
                self.bot.session,
                repo,
                issue_id,
                comment_wrap_contextless(body, message)
            )
        await message.add_reaction("✅" if status else "🚫")

    async def process_github_links(self, message: Message):
        content = message.content
        links = re.findall(self.url_regex, content)
        links = [link[0] for link in links]
        for link in links:
            if link.endswith("/"):
                link = link[:-1]
            repo_name, link_type, object_id = link.split("/")[-3:]
            if repo_name not in self.private_repos:
                continue
            if link_type == "issues":
                status, data = await get_issue_by_number(self.bot.session, repo_name, object_id)
                if not status:
                    continue
                embed = get_issue_embed(data, object_id, repo_name, link)
                view = IssueControls(self.bot.session, repo_name, object_id)
                await message.channel.send(embed=embed, view=view)
            elif link_type == "pull":
                status, data = await get_pull_request_by_number(self.bot.session, repo_name, object_id)
                if not status:
                    continue
                embed = get_pull_request_embed(data, object_id, repo_name, link)
                view = IssueControls(self.bot.session, repo_name, object_id)
                await message.channel.send(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user == self.bot.user or not reaction.message.embeds:
            return
        message = reaction.message
        embed = message.embeds[0]
        author = embed.author

        if not embed or message.author != self.bot.user:
            return

        if reaction.emoji not in PAGE_CONTROLS:
            return

        await message.remove_reaction(reaction.emoji, user)

        params = [param.lower() for param in author.name.split(" ")]
        if params[0] == "issues:":
            page_number = int(embed.footer.text.split(" ")[1]) + PAGE_CONTROLS[reaction.emoji]
            count = params[1]
            state = params[2]
            repo = params[4]
            new_description = await get_issues_list(self.bot.session, repo, state, count, page_number)

            title = f"Issues: {count} {state.capitalize()} in {repo}"
            footer = f"Page: {page_number}"
            await message.edit(embed=update_embed(embed, new_description, title, footer))

    @commands.command()
    async def check_input_waiting(self, context: Context):
        selected = await get_selectable_argument(
            context, "What's your chosen thing?", ["yes", "no", "maybe", "perhaps", "1", "2", "3"]
        )
        await context.send(f"You selected: {selected}")

    @commands.command()
    async def check_dropdown(self, context: Context):
        selected = await get_dropdown_argument(
            context, "Drop that down!", ["yes", "no", "maybe", "perhaps", "1", "2", "3"]
        )
        await context.send(f"You selected: {selected}")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def add_github_name(self, context: Context, user: Member, github_name: str):
        await context.trigger_typing()
        await context.bot.redis.hset("github_mention", user.mention, github_name)
        await context.send(f"Successfully assigned {user.mention} to github name **{github_name}**")

    @commands.command()
    async def github_name(self, context: Context, user: Member):
        await context.trigger_typing()
        github_name = await context.bot.redis.hget("github_mention", user.mention, encoding="utf8")
        if github_name:
            msg = f"Github username of {user.mention} is **{github_name}**"
        else:
            msg = f"No associated Github username for {user.mention} stored!"
        await context.send(msg)

    @commands.command(name="issue", aliases=["i", "issues", "Issues", "I"])
    async def issue(self, context: Context, *args):
        if len(args) == 0:
            embed = Embed(
                description="Shortcuts are case-insensitive",
                timestamp=datetime.utcnow(),
                colour=colour.Color.dark_teal()
            )
            shortcuts = "\n".join([f"{key.ljust(10)} => {value}" for key, value in preset_repos.items()])
            embed.add_field(name="Shortcuts: ", value=f"```{shortcuts}```", inline=False)
            usage = """
    `$add_github_name @mention github_username` - assign github name to mentioned user
    `$github_name @mention` - get assigned github name of mentioned user
    `$issue [repo name] "[title]" "[description]"` - open shortcut
    `$issue [command]` - bot guidance
    `$issue open war "Test" "Test"` - example of full command for issue opening
            """
            embed.add_field(name="Usage", value=usage, inline=False)
            command_types = """
```
[o] open    - open an issue
[c] close   - close an issue
[e] edit    - edit issue' body and title
[at] attach - attach image to issue (as a comment)
[c] comment - send comment to issue (any text)
[l] list    - list of issues in repo (filtered with -all, -open, -closed)
[as] assign - assign users to specific issue
[s] search  - search issues using github query syntax
```
            """
            embed.add_field(name="Command types", value=command_types, inline=False)
            reply_description = """
                You can reply to "Opened new issue..." messages from bot to interact with newly opened issue directly.
                Text is interpreted as comments, image attachments are supported.
                Also can be used with starting keyword for different actions:
```
label: bug "help wanted" enhancement "under review"
assign: darklordabc SanctusAnimus ZLOY5
close: duplicate of #12
```
            """
            embed.add_field(name="Replying", value=reply_description, inline=False)
            await context.send(embed=embed)
            return
        action = args[0]
        args = args[1:]
        await self.handle_bot_command(context, action.lower(), *args)

    @commands.command()
    async def update_repos(self, context: commands.Context):
        await github_init(context.bot)

    async def handle_bot_command(self, context, action, *args):
        args_len = len(args)
        await context.trigger_typing()
        repo = None
        if action in preset_repos:
            repo = preset_repos[action]
            action = "open"
            args = ["", ] + list(args)
            args_len += 1

        if not repo:
            if args_len > 0:
                repo = args[0]
            else:
                repo = await get_selectable_argument(
                    context,
                    f"Select repo:", preset_repos.keys()
                )
            if repo.lower() in preset_repos:
                repo = preset_repos[repo.lower()]
        if not repo:
            return
        await context.trigger_typing()
        for aliases, coro in self.command_list:
            if action in aliases:
                return await coro(context, repo, args, args_len)

    @staticmethod
    async def _list_issues(context: Context, repo: str, args: List[str], args_len: int) -> None:
        state = "open"
        if '-closed' in args: state = "closed"
        if '-all' in args: state = "all"

        count = 10
        page = 1

        embed = Embed(
            description=await get_issues_list(context.bot.session, repo, state, count, page),
            timestamp=datetime.utcnow(),
            colour=colour.Color.dark_teal()
        )

        embed.set_author(
            name=f"Issues: {count} {state.capitalize()} in {repo}",
            url=f"https://github.com/arcadia-redux/{repo}/issues",
            icon_url="https://cdn.discordapp.com/attachments/684952282076282882/838854388201553930/123.png"
        )

        embed.set_footer(text=f"Page: {page}")

        message = await context.send(embed=embed)
        await asyncio.gather(*[message.add_reaction("⏮"), message.add_reaction("⏭")])

    @staticmethod
    async def _close_issue(context: Context, repo: str, args: List[str], args_len: int) -> None:
        issue_id = args[1] if args_len > 1 else await get_argument(context, "Waiting for issue id:")
        status, detail = await close_issue(context.bot.session, repo, issue_id)
        if status:
            await context.send(f"Successfully closed issue **#{issue_id}** of **{repo}**")
        else:
            await context.send(f"GitHub error occurred:\n{detail}")

    @staticmethod
    async def _open_issue(context: Context, repo: str, args: List[str], args_len: int) -> None:
        title = args[1] if args_len > 1 else None
        body = args[2] if args_len > 2 else ''
        if not title:
            argument = await get_argument(
                context,
                f"Waiting for title. You may add description on the new line of the same message."
            )
            if '\n' not in argument:
                argument += '\n '
            title, body = argument.split("\n")
        if context.message.attachments:
            body += await process_attachments(context, context.message.attachments[0].url)
        status, details = await open_issue(context, repo, title, body)

        if status:
            embed = Embed(
                description=f"Reply to this message to interact with new issue",
                colour=colour.Colour.green(),
                timestamp=datetime.utcnow(),
            )
            embed.set_author(
                icon_url=str(context.message.author.avatar),
                name=f"Opened issue #{details['number']} in {repo}",
                url=details['html_url']
            )
            control_view = IssueControls(context.bot.session, repo, details['number'])
            msg = await context.send(embed=embed, view=control_view)
            control_view.assign_message(msg)
        else:
            await context.reply(f"GitHub error occurred:\n{details}.")

    @staticmethod
    async def _edit_issue(context: Context, repo: str, args: List[str], args_len: int) -> None:
        issue_id = args[1] if args_len > 1 else await get_argument(context, "Waiting for issue id:")
        title = args[2] if args_len > 2 else None
        body = args[3] if args_len > 3 else ''
        if not title:
            argument = await get_argument(
                context,
                f"Waiting for title. You may add description on the new line of the same message."
            )
            if '\n' not in argument:
                argument += '\n'
            title, body = argument.split("\n")
        status, details = await update_issue(context, repo, title, body, issue_id)
        if status:
            await context.reply(f"Successfully updated issue #{issue_id}")
        else:
            await context.reply(f"GitHub error occurred:\n{details}")

    @staticmethod
    async def _attach_image(context: Context, repo: str, args: List[str], args_len: int) -> None:
        issue_id = args[1] if args_len > 1 else await get_argument(context, "Waiting for issue id:")
        if context.message.attachments:
            attachment = context.message.attachments[0]
        else:
            message = await context.send("Awaiting for attachment.")
            try:
                result = await context.bot.wait_for(
                    "message",
                    check=lambda message: message.author == context.message.author and message.attachments,
                    timeout=120
                )
            except TimeoutError:
                await message.delete()
                return
            if not result.attachments:
                await message.delete()
                return
            attachment = result.attachments[0]
        status, link = await comment_issue(
            context.bot.session,
            repo,
            issue_id,
            comment_wrap(await process_attachments(context, attachment.url), context)
        )
        if status:
            await context.send(f"Successfully added comment {link}")
        else:
            await context.send(f"Github error occurred: {link}")

    @staticmethod
    async def _comment_issue(context: Context, repo: str, args: List[str], args_len: int) -> None:
        issue_id = args[1] if args_len > 1 else await get_argument(context, "Waiting for issue id:")
        content = args[2] if args_len > 2 else await get_argument(context, "Waiting for comment text:")
        status, link = await comment_issue(context.bot.session, repo, issue_id, comment_wrap(content, context))
        if status:
            await context.send(f"Successfully added comment {link}")
        else:
            await context.send(f"Github error occurred: {link}")

    @staticmethod
    async def _assign_to_issue(context: Context, repo: str, args: List[str], args_len: int) -> None:
        logger.info("assign called")
        issue_id = args[1] if args_len > 1 else await get_argument(context, "Waiting for issue id:")
        assignees = args[2:] if args_len > 2 else (await get_argument(context, "Waiting for assignees: ")).split(" ")
        status, details = await assign_issue(context.bot.session, repo, issue_id, assignees)
        if status:
            await context.send(f"Successfully assigned **{', '.join(assignees)}** to issue **{issue_id}**")
        else:
            await context.send(f"Github error occurred:\n```{details}```")

    @staticmethod
    async def _search_issues(context: Context, repo: str, args: List[str], args_len: int) -> None:
        if args_len > 1:
            query = " ".join(args[1:])
        else:
            query = await get_argument(context, "Waiting for search query:")
        status, details = await search_issues(context.bot.session, repo, query)

        if not status:
            await context.send(f"Github error occurred:\n```{details}```")
            return

        results = details["total_count"]
        description = []
        for item in details["items"]:
            link = f"[`#{item['number']}`]({item['html_url']})"
            issue_state = "🟢" if item['state'] == "open" else "🔴"
            description.append(
                f"{issue_state} {link} {item['title']}"
            )

        description.append(
            f"\n[`How to compose queries`](https://docs.github.com/en/github/searching-for-information-on-github/searching-on-github/searching-issues-and-pull-requests#search-only-issues-or-pull-requests)")

        embed = Embed(
            title=f"Total search results: {results} {'listing 10' if results > 10 else ''}",
            description="\n".join(description),
            timestamp=datetime.utcnow(),
            colour=colour.Colour.blurple(),
        )
        embed.set_author(name=f"Search in {repo}", url=f"https://github.com/arcadia-redux/{repo}")
        await context.send(embed=embed)
