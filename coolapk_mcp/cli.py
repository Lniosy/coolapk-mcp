"""CLI 入口 — 精简 JSON 输出，节省 token"""

import asyncio
import json
import sys
from functools import wraps

import click

from coolapk_mcp.client import CoolapkClient, CoolapkError
from coolapk_mcp.models import (
    AppModel,
    FeedDetail,
    FeedModel,
    ReplyModel,
    TopicModel,
    UserModel,
)


def _dump(obj):
    """模型 → dict，排除默认值"""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json", exclude_defaults=True)
    return obj


def _output(data):
    """统一 JSON 输出，紧凑格式节省 token"""
    if data is None:
        click.echo(json.dumps({"error": "无数据"}, ensure_ascii=False))
        sys.exit(1)
    if isinstance(data, list):
        data = [_dump(item) for item in data]
    else:
        data = _dump(data)
    click.echo(json.dumps(data, ensure_ascii=False))


def async_command(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        asyncio.run(f(*args, **kwargs))
    return wrapper


@click.group()
def cli():
    """酷安社区 CLI — AI 原生搜索工具"""
    pass


# ---- 浏览 ----


@cli.command("home")
@click.option("--tab", type=click.Choice(["recommend", "hot", "latest"]), default="recommend")
@click.option("--page", default=1, type=int)
@async_command
async def home(tab, page):
    """首页动态"""
    async with CoolapkClient() as client:
        if tab == "hot":
            raw = await client.get_hot_feeds(page)
        elif tab == "latest":
            raw = await client.get_latest_feeds(page)
        else:
            raw = await client.get_home_feeds(page)
    feeds = [FeedModel.from_api(f) for f in raw] if isinstance(raw, list) else raw
    _output(feeds)


@cli.command("feed")
@click.argument("feed_id", type=int)
@click.option("--replies/--no-replies", default=True)
@click.option("--reply-page", default=1, type=int)
@async_command
async def feed(feed_id, replies, reply_page):
    """动态详情"""
    async with CoolapkClient() as client:
        raw = await client.get_feed_detail(feed_id)
        if isinstance(raw, list) and raw:
            raw = raw[0]
        if not isinstance(raw, dict):
            _output(raw)
            return
        reply_data = None
        if replies:
            reply_data = await client.get_feed_replies(feed_id, reply_page)
        detail = FeedDetail.from_api(
            raw, reply_data if isinstance(reply_data, list) else None
        )
    _output(detail)


# ---- 搜索 ----


@cli.command("search")
@click.argument("keyword")
@click.option("--type", "search_type", default="feed",
              type=click.Choice(["feed", "user", "feedTopic", "app"]))
@click.option("--page", default=1, type=int)
@async_command
async def search(keyword, search_type, page):
    """搜索内容"""
    async with CoolapkClient() as client:
        raw = await client.search(keyword, search_type, page)
    if not isinstance(raw, list):
        _output(raw)
        return
    results = []
    for item in raw:
        if not isinstance(item, dict):
            results.append(item)
            continue
        et = item.get("entityType", "")
        if et == "feed":
            results.append(FeedModel.from_api(item))
        elif et == "user":
            results.append(UserModel.from_api(item))
        elif et in ("topic", "tag"):
            results.append(TopicModel.from_api(item))
        elif et == "app":
            results.append(AppModel.from_api(item))
        else:
            results.append(item)
    _output(results)


# ---- 用户 ----


@cli.command("user")
@click.argument("uid", type=int)
@click.option("--feeds", is_flag=True, help="查看用户动态")
@click.option("--page", default=1, type=int)
@async_command
async def user(uid, feeds, page):
    """查看用户"""
    async with CoolapkClient() as client:
        if feeds:
            raw = await client.get_user_feeds(uid, page)
            _output([FeedModel.from_api(f) for f in raw] if isinstance(raw, list) else raw)
        else:
            raw = await client.get_user_space(uid)
            if isinstance(raw, list) and raw:
                raw = raw[0]
            _output(UserModel.from_api(raw) if isinstance(raw, dict) else raw)


# ---- 话题 ----


@cli.command("topic")
@click.argument("tag")
@click.option("--feeds", is_flag=True, help="查看话题下的帖子")
@click.option("--page", default=1, type=int)
@async_command
async def topic(tag, feeds, page):
    """话题详情"""
    async with CoolapkClient() as client:
        if feeds:
            raw = await client.get_topic_feeds(tag, page)
            _output([FeedModel.from_api(f) for f in raw] if isinstance(raw, list) else raw)
        else:
            raw = await client.get_topic_detail(tag)
            if isinstance(raw, list) and raw:
                raw = raw[0]
            _output(TopicModel.from_api(raw) if isinstance(raw, dict) else raw)


# ---- 通知 ----


@cli.command("notify")
@click.argument("ntype", default="checkCount",
                type=click.Choice(["checkCount", "atMeMeFeed", "atComment", "comment", "feedLike", "contactsFollow", "message"]))
@click.option("--page", default=1, type=int)
@async_command
async def notify(ntype, page):
    """查看通知"""
    async with CoolapkClient() as client:
        if ntype == "checkCount":
            data = await client.get_notification_count()
        else:
            data = await client.get_notifications(ntype, page)
    _output(data)


# ---- 交互 ----


@cli.command("like")
@click.argument("feed_id", type=int)
@async_command
async def like(feed_id):
    """点赞"""
    async with CoolapkClient() as client:
        data = await client.like_feed(feed_id)
    _output(data)


@cli.command("unlike")
@click.argument("feed_id", type=int)
@async_command
async def unlike_cmd(feed_id):
    """取消赞"""
    async with CoolapkClient() as client:
        data = await client.unlike_feed(feed_id)
    _output(data)


@cli.command("reply")
@click.argument("target_id", type=int)
@click.option("--message", "-m", required=True)
@click.option("--type", "reply_type", type=click.Choice(["feed", "reply"]), default="feed")
@async_command
async def reply(target_id, message, reply_type):
    """回复"""
    async with CoolapkClient() as client:
        if reply_type == "feed":
            data = await client.reply_feed(target_id, message)
        else:
            data = await client.reply_reply(target_id, message)
    _output(data)


@cli.command("follow")
@click.argument("uid", type=int)
@async_command
async def follow(uid):
    """关注用户"""
    async with CoolapkClient() as client:
        data = await client.follow_user(uid)
    _output(data)


@cli.command("unfollow")
@click.argument("uid", type=int)
@async_command
async def unfollow(uid):
    """取消关注"""
    async with CoolapkClient() as client:
        data = await client.unfollow_user(uid)
    _output(data)


# ---- 登录 ----


@cli.command("login")
@click.option("--cookie", help="Cookie 字符串 (uid=xxx;username=xxx;token=xxx)")
@click.option("--status", is_flag=True, help="查看登录状态")
@async_command
async def login(cookie, status):
    """登录管理"""
    from coolapk_mcp.config import AppConfig

    config = AppConfig.load()
    if status:
        _output({
            "logged_in": config.is_logged_in,
            "uid": config.uid,
            "username": config.username,
        })
        return

    if cookie:
        parts = {}
        for item in cookie.split(";"):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                parts[k.strip()] = v.strip()
        config.uid = parts.get("uid", "")
        config.username = parts.get("username", "")
        config.token = parts.get("token", "")
        config.save()
        _output({"status": "ok", "uid": config.uid, "username": config.username})
    else:
        click.echo(json.dumps({"error": "请使用 --cookie 传入 Cookie 或 --status 查看状态"}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    cli()
