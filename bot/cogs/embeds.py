from discord import Embed
from datetime import datetime
from discord.colour import Colour


def get_issue_embed(data: dict, object_id: str, repo_name: str, link: str) -> Embed:
    labels = ", ".join([f"`{label['name']}`" for label in data['labels']])
    assignees = ", ".join([f"`{assignee['login']}`" for assignee in data['assignees']])
    description = [
        f"**Labels**: {labels}" if labels else "",
        f"**Assignees**: {assignees}" if assignees else "",
        f'\n{data["body"]}' if len(data["body"]) < 400 else "",
    ]
    embed = Embed(
        title=data['title'],
        description="\n".join(description),
        colour=Colour.green() if data['state'] == "open" else Colour.red(),
    )
    embed.set_author(
        name=f"Linked issue #{object_id} in {repo_name} by {data['user']['login']}",
        url=link,
        icon_url=data["user"]["avatar_url"],
    )
    opened_at_date = datetime.strptime(data['created_at'], "%Y-%m-%dT%H:%M:%SZ")
    embed.set_footer(text=f"{data['comments']} Comment{'s' if data['comments'] != 1 else ''} "
                          f"| Opened at {opened_at_date.strftime('%c')}")
    return embed


def get_pull_request_embed(data: dict, object_id: str, repo_name: str, link: str) -> Embed:
    labels = ", ".join([f"`{label['name']}`" for label in data['labels']])
    assignees = ", ".join([f"`{assignee['login']}`" for assignee in data['assignees']])
    reviewers = ", ".join([f"`{reviewer['login']}`" for reviewer in data["requested_reviewers"]])
    merge_state = ""
    color = Colour.green()
    if data['draft']:
        merge_state = "draft"
        color = Colour.dark_grey()
    elif data['merged']:
        merge_state = "merged"
        color = Colour.dark_purple()
    elif data["mergeable"]:
        merge_state = data['mergeable_state']
        if merge_state in ["blocked", "behind"]:
            color = Colour.red()
        elif merge_state == "dirty":
            color = Colour.dark_orange()
    description = [
        f"**Labels**: {labels}" if labels else "",
        f"**Assignees**: {assignees}" if assignees else "",
        f"**Reviewers**: {reviewers}" if reviewers else "",
        f"**Changes**: {data['commits']} commit{'s' if data['commits'] != 1 else ''}, "
        f"`+{data['additions']}` : `-{data['deletions']}` in {data['changed_files']} files",
        f"**Merge state:** `{merge_state}`",
        f'\n{data["body"]}' if len(data["body"]) < 400 else "",
    ]
    embed = Embed(
        title=data['title'],
        description="\n".join(description),
        colour=color,
    )
    embed.set_author(
        name=f"Linked PR #{object_id} in {repo_name} by {data['user']['login']}",
        url=link,
        icon_url=data['user']['avatar_url']
    )
    opened_at_date = datetime.strptime(data['created_at'], "%Y-%m-%dT%H:%M:%SZ")
    embed.set_footer(text=f"{data['comments']} Comment{'s' if data['comments'] != 1 else ''} "
                          f"| Opened at {opened_at_date.strftime('%c')}")
    return embed
