from base64 import b64encode
from os import getenv
from typing import Optional, List, Tuple, Union
from aiohttp import ClientSession

from discord.ext.commands import Context
from loguru import logger

login = getenv("GITHUB_LOGIN")
password = getenv("GITHUB_KEY")
auth_string = b64encode(f"{login}:{password}".encode("ascii")).decode("ascii")

base_api_link = "https://api.github.com"
base_api_headers = {
    "Authorization": f"Basic {auth_string}",
    "Accept": "application/vnd.github.v3+json",
}
repositories = []

preset_repos = {
    "chc": "custom_hero_clash_issues",
    "12v12": "12v12",
    "ot": "overthrow2",
    "revolt": "reVolt",
    "war": "war_masters",
    "bot": "arcadia_automation_bot",
}

preset_repos_reverse = {value: key for key, value in preset_repos.items()}

excluded_global_repos = {
    "who_will_win_server", "custom_game_encrypter", "server", "Aghanims_Editor", "resources", "who_will_win",
    "aghslab2", "contest.dota2unofficial.com"
}

_Numeric = Union[str, int]
_ApiResponse = Tuple[bool, dict]


async def github_init(bot) -> str:
    return await get_repos(bot)


def body_wrap(body: str, context: Context) -> str:
    return f"{body if body else ''}\n\nOpened from Discord by " \
           f"**{context.author.name}#{context.author.discriminator}**\n" \
           f"Follow the conversation [here]({context.message.jump_url})"


def comment_wrap(body: str, context: Context) -> str:
    return f"{body if body else ''}\n\nComment from Discord by " \
           f"**{context.author.name}#{context.author.discriminator}**\n" \
           f"Follow the conversation [here]({context.message.jump_url})"


def comment_wrap_contextless(body: str, message) -> str:
    return f"{body if body else ''}\n\nComment from Discord by " \
           f"**{message.author.name}#{message.author.discriminator}**\n" \
           f"Follow the conversation [here]({message.jump_url})"


async def open_issue(context: Context, repo: str, title: str, body: Optional[str] = "") -> _ApiResponse:
    issue_body = {
        "title": title,
        "body": body_wrap(body, context),
    }
    resp = await context.bot.session.post(
        f"{base_api_link}/repos/arcadia-redux/{repo}/issues", json=issue_body, headers=base_api_headers
    )
    return resp.status < 400, await resp.json()


async def close_issue(session: ClientSession, repo: str, issue_id: _Numeric) -> _ApiResponse:
    issue_body = {
        "state": "closed"
    }
    resp = await session.patch(
        f"{base_api_link}/repos/arcadia-redux/{repo}/issues/{issue_id}", json=issue_body, headers=base_api_headers,
    )
    return resp.status < 400, await resp.json()


async def update_issue(context: Context, repo: str, title: str, body: str, issue_id: _Numeric) -> _ApiResponse:
    issue_body = {
        "title": title,
        "body": body_wrap(body, context),
    }
    resp = await context.bot.session.patch(
        f"{base_api_link}/repos/arcadia-redux/{repo}/issues/{issue_id}", json=issue_body, headers=base_api_headers,
    )
    return resp.status < 400, await resp.json()


async def add_labels(session: ClientSession, repo: str, issue_id: _Numeric, labels: List[str]):
    issue_body = {
        "labels": labels
    }
    resp = await session.patch(
        f"{base_api_link}/repos/arcadia-redux/{repo}/issues/{issue_id}", json=issue_body, headers=base_api_headers,
    )
    return resp.status < 400, await resp.json()


async def assign_issue(session: ClientSession, repo: str, issue_id: _Numeric, assignees: List[str]) -> _ApiResponse:
    issue_body = {
        "assignees": assignees,
    }
    logger.info(f"{base_api_link}/repos/arcadia-redux/{repo}/issues/{issue_id}/assignees")
    resp = await session.post(
        f"{base_api_link}/repos/arcadia-redux/{repo}/issues/{issue_id}/assignees",
        json=issue_body,
        headers=base_api_headers
    )
    return resp.status < 400, await resp.json()


async def get_repos(bot) -> str:
    global repositories
    resp = await bot.session.get(f"{base_api_link}/orgs/arcadia-redux/repos", headers=base_api_headers)
    if resp.status >= 400:
        logger.warning(f"Error when fetching org repos: {await resp.body()}")
        return ""
    response = await resp.json()
    repositories.clear()
    for repo in response:
        if repo["name"] not in excluded_global_repos:
            preset_name = f' [{preset_repos_reverse[repo["name"]]}]' if repo["name"] in preset_repos_reverse else ""
            repositories.append(f'`{repo["name"]}{preset_name}`')
    repositories.sort()
    return '\n'.join(repositories)


async def get_issues_list(session: ClientSession, repo: str, state: str, count: _Numeric, page: _Numeric) -> str:
    resp = await session.get(
        f"{base_api_link}/repos/arcadia-redux/{repo}/issues?per_page={count}&state={state}&page={page}",
        headers=base_api_headers
    )
    if resp.status >= 400:
        return ""
    response = await resp.json()
    description_list = []
    for issue in response:
        issue_state = "🟢" if issue['state'] == "open" else "🔴"
        description_list.append(
            f"{issue_state} [`#{issue['number']}`]({issue['html_url']}) {issue['title']}"
        )
    return "\n".join(description_list)


async def get_issue_by_number(session: ClientSession, repo: str, issue_id: _Numeric) -> _ApiResponse:
    resp = await session.get(f"{base_api_link}/repos/arcadia-redux/{repo}/issues/{issue_id}", headers=base_api_headers)
    return resp.status <= 400, await resp.json()


async def get_pull_request_by_number(session: ClientSession, repo: str, pull_id: _Numeric) -> _ApiResponse:
    resp = await session.get(f"{base_api_link}/repos/arcadia-redux/{repo}/pulls/{pull_id}", headers=base_api_headers)
    return resp.status <= 400, await resp.json()


async def get_commit_by_sha(session: ClientSession, repo: str, sha: str) -> _ApiResponse:
    resp = await session.get(f"{base_api_link}/repos/arcadia-redux/{repo}/commits/{sha}", headers=base_api_headers)
    return resp.status <= 400, await resp.json()


async def get_commits_diff(session: ClientSession, repo: str, base: str, head: str) -> _ApiResponse:
    resp = await session.get(
        f"{base_api_link}/repos/arcadia-redux/{repo}/compare/{base}...{head}",
        headers=base_api_headers
    )
    return resp.status <= 400, await resp.json()


async def get_repo_labels(session: ClientSession, repo: str) -> _ApiResponse:
    resp = await session.get(
        f"{base_api_link}/repos/arcadia-redux/{repo}/labels", headers=base_api_headers
    )
    return resp.status <= 400, await resp.json()


async def get_arcadia_team_members(session: ClientSession) -> _ApiResponse:
    resp = await session.get(
        f"{base_api_link}/organizations/46830822/team/4574724/members", headers=base_api_headers
    )
    return resp.status <= 400, await resp.json()


async def comment_issue(session: ClientSession, repo: str, issue_id: _Numeric, body: str) -> Tuple[bool, Union[dict, str]]:
    resp = await session.post(
        f"{base_api_link}/repos/arcadia-redux/{repo}/issues/{issue_id}/comments",
        json={"body": body},
        headers=base_api_headers
    )
    if resp.status >= 400:
        return False, await resp.json()
    return True, (await resp.json())["html_url"]


async def search_issues(session: ClientSession, repo: str, query: str,
                        page_num: Optional[_Numeric] = 1) -> _ApiResponse:
    request_body = {
        "q": f"repo:arcadia-redux/{repo} {query}",
        "per_page": 10,
        "page": page_num
    }

    resp = await session.get(
        f"{base_api_link}/search/issues", headers=base_api_headers, params=request_body
    )
    return resp.status < 400, await resp.json()

