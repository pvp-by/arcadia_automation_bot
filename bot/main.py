import asyncio
import datetime
import json
import os
from typing import Final

from __load_env import LOCALS_IMPORTED  # True if imported local .env file

import aiohttp
import aioredis
import discord
from aioredis.pubsub import Receiver
from discord.ext import commands
from loguru import logger

from cogs import github_cog, core_cog
from enums import BotState
from translator import translate

PREFIX: Final = "$" if not LOCALS_IMPORTED else "%"
token = os.getenv("BOT_TOKEN", None)

__BOT_STATE = BotState.UNSET

bot = commands.Bot(command_prefix=PREFIX)
bot.session = aiohttp.ClientSession()
bot.add_cog(github_cog.Github(bot))
bot.add_cog(core_cog.Core(bot))

# ew, hardcode
SERVER_LINKS = {
    "CustomHeroClash": "https://chc-2.dota2unofficial.com/",
    "Dota12v12": "https://api.12v12.dota2unofficial.com/",
    "Overthrow": "https://api.overthrow.dota2unofficial.com/",
    "WarMasters": "https://api.warmasters.dota2unofficial.com/",
}

langs = {
    "addon_english": "English",
    "addon_russian": "Russian",
    "addon_tchinese": "T. Chinese",
    "addon_schinese": "S. Chinese"
}

bot.report_channels = {key: None for key in SERVER_LINKS.keys()}
bot.translation_channel = None

webapi_key = os.getenv("WEBAPI_KEY")


@bot.event
@logger.catch
async def on_ready():
    global __BOT_STATE
    if __BOT_STATE == BotState.SET:
        logger.info(f"Bot is already in state [SET], skipping")
        return
    logger.info("[Ready] Started")
    url = os.getenv("REDIS_URl")
    pwd = os.getenv("PWD")
    bot.redis = await aioredis.create_redis_pool(url, password=pwd)

    logger.add("exec.log", rotation="1 day", retention="1 week", enqueue=True)
    logger.add("error.log", rotation="1 day", retention="1 week", enqueue=True, level="ERROR")

    for custom_game in bot.report_channels.keys():
        executor = bot.redis.multi_exec()
        executor.get(f"{custom_game}-report-channel-id")
        executor.get(f"{custom_game}-report-channel-name")
        ch_id, name = await executor.execute()

        logger.info(f"[{custom_game}] Assigned report channel: {ch_id}:{name}")
        if ch_id and name:
            bot.report_channels[custom_game] = bot.get_channel(int(ch_id))

    receiver = Receiver()

    @logger.catch
    async def reader(channel):
        async for ch, message in channel.iter():
            await send_suggestion(message[1])
        logger.info("finished reading!")

    bot.task = asyncio.ensure_future(reader(receiver))
    await bot.redis.psubscribe(receiver.pattern('suggestions:*'))

    __BOT_STATE = BotState.SET
    logger.info(f"[Ready] Finished")


@bot.command()
async def state(ctx):
    await ctx.send(__BOT_STATE)


@logger.catch
async def send_suggestion(message):
    decoded = json.loads(message)
    custom_game = decoded["custom_game"]
    steam_id = decoded["steam_id"]
    text = decoded["text"]

    logger.info(f"Message from channel {custom_game} by {steam_id}: {text}")

    translated, language = await translate(text)

    report_channel = bot.report_channels.get(custom_game, None)
    if not report_channel:
        return

    resp = await bot.session.get(
        f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={webapi_key}&steamids={steam_id}"
    )
    steam_profile_data = None
    if resp.status == 200:
        steam_profile_data = await resp.json()

    profile_avatar_link, profile_name = None, None
    if steam_profile_data:
        steam_profile_data = steam_profile_data["response"]["players"][0]
        profile_avatar_link = steam_profile_data["avatarmedium"]
        profile_name = steam_profile_data["personaname"]

    embed = discord.Embed(
        timestamp=datetime.datetime.utcnow(),
        description=f'```{decoded["text"].strip()}```',
    )
    embed.set_author(
        name=profile_name,
        url=f"https://steamcommunity.com/profiles/{steam_id}",
        icon_url=profile_avatar_link or ""
    )
    if translated:
        embed.add_field(name=f"Translation from **{language.upper()}**", value=f"```{translated}```")

    if custom_game == "CustomHeroClash" and steam_id:
        embed.add_field(
            name=f"Reward",
            value=" | ".join(
                f"[{i}<:fortune:831077783446749194>](https://chc-2.dota2unofficial.com/admin/management"
                f"/add_fortune?steam_id={steam_id}&fortune_amount={i})" for i in
                [5, 10, 25, 50, 100]),
            inline=False
        )

    await report_channel.send(embed=embed)


@bot.event
@commands.has_permissions(manage_messages=True)
async def on_message(message):
    if message.author.bot:
        return

    message_text = message.content
    if not message_text.startswith(PREFIX) or bot.get_cog("Core").reserved(message_text):
        await bot.process_commands(message)
        return

    command_key = message_text.split(" ")[0][1:]
    if command_value := await bot.redis.lrange(command_key, 0, 100):
        result = "\n".join([val.decode("utf-8") for val in command_value])
        await message.channel.send(result)

    await bot.process_commands(message)


@bot.event
@logger.catch
async def on_command_error(context, err):
    logger.error(f"[ON_COMMAND] {err.args!r}")


bot.run(token)
