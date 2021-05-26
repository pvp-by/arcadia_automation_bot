import json
import os
import sys
from asyncio import sleep
from hashlib import sha256

import aioredis
from aiohttp import web, ClientSession
from loguru import logger

from loc_issue_manager import publish_localization_changes, get_api_headers

routes = web.RouteTableDef()


async def publish(app: web.Application, redis, data: dict):
    try:
        logger.info(f"publishing data: {data}")
        await redis.publish("modified:localization", json.dumps(data))
    except:
        logger.warning(f"{sys.exc_info()[0]}")
        url = os.getenv("REDIS_URl")
        pwd = os.getenv("PWD")
        app["redis"] = await aioredis.create_redis_pool(url, password=pwd, maxsize=2)
        await sleep(2)
        await publish(app, app["redis"], data)


@routes.post("/push")
async def github_event_handler(request: web.Request):
    logger.info("push handler triggered")
    data = await request.json()
    redis = request.app["redis"]
    session = request.app["session"]

    if data["ref"] != "refs/heads/master" and data["ref"] != "refs/heads/main":
        logger.info(f"Github event ref ain't master: {data['ref']}")
        return

    sent_data = {
        "repo": {
            "name": data["repository"]["full_name"].replace("arcadia-redux/", "").replace("SanctusAnimus/", ""),
            "base_url": data["repository"]["html_url"],
            "url": data["repository"]["html_url"].replace("github.com", "api.github.com/repos")
        },
        "compare": data["compare"],
        "pusher": data["pusher"]["name"],
        "file": {},
        "before": data['before'],
        "after": data['after'],
    }

    diff_res = await session.get(
        f"{sent_data['repo']['url']}/compare/{data['before']}...{data['after']}",
        headers=get_api_headers()
    )
    if diff_res.status < 400:
        logger.info(f"got the diff!")
        diff_data = await diff_res.json()
        addon_english_file = next(
            (file for file in diff_data["files"] if "addon_english.txt" in file["filename"]),
            None
        )
        if addon_english_file:
            logger.info(f"got addon english file")
            # pointer to addon_english changes inside diff, for ease of use
            sent_data["anchor"] = sha256(addon_english_file['filename'].encode('utf-8')).hexdigest()
            sent_data["file"] = addon_english_file
            await publish_localization_changes(session, redis, sent_data)
        else:
            logger.warning(f"no addon english file")
    else:
        logger.warning(f"haven't got the diff: {await diff_res.json()}")

    return web.Response(status=200)


@routes.get("/test")
async def test(request: web.Request):
    logger.info(f"test request running")
    redis = request.app["redis"]
    result = [val.decode("utf-8") for val in await redis.lrange("bath8", 0, 100)]
    return web.json_response({"test": result})


async def init():
    url = os.getenv("REDIS_URl")
    pwd = os.getenv("PWD")

    app = web.Application()
    app["redis"] = await aioredis.create_redis_pool(url, password=pwd, maxsize=2)
    app["session"] = ClientSession()
    app.add_routes(routes)
    return app


web.run_app(init(), host="0.0.0.0", port=80)
