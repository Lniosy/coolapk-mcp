"""CLI 入口 — 精简 JSON 输出，节省 token"""

import asyncio
import json
import sys
from functools import wraps

import click

from coolapk_mcp.boards import BOARD_URLS
from coolapk_mcp.client import CoolapkClient, CoolapkError
from coolapk_mcp.models import (
    AppModel,
    ChatSessionModel,
    FeedDetail,
    FeedModel,
    MessageModel,
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


def _output_error(err: CoolapkError):
    """错误输出"""
    click.echo(json.dumps(
        {"error": err.message, "code": err.error_code},
        ensure_ascii=False,
    ))
    sys.exit(1)


def async_command(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            asyncio.run(f(*args, **kwargs))
        except CoolapkError as e:
            _output_error(e)
        except KeyboardInterrupt:
            sys.exit(130)
    return wrapper


def _parse_feeds(raw) -> list[FeedModel]:
    """从 dataList 原始响应解析 feed 列表，自动过滤 card 条目"""
    if not isinstance(raw, list):
        return []
    feeds = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        if item.get("entityType") == "feed":
            feeds.append(FeedModel.from_api(item))
        # card 内嵌的 entities 也可能是 feed
        elif item.get("entityType") == "card":
            for sub in item.get("entities") or []:
                if isinstance(sub, dict) and sub.get("entityType") == "feed":
                    feeds.append(FeedModel.from_api(sub))
    return feeds


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
    _output(_parse_feeds(raw))


@cli.command("main")
@click.option("--page", default=1, type=int)
@async_command
async def main(page):
    """首页推荐（main/indexV8）"""
    async with CoolapkClient() as client:
        raw = await client.get_main_feeds(page)
    _output(_parse_feeds(raw))


@cli.command("hot")
@click.option("--page", default=1, type=int)
@async_command
async def hot(page):
    """热榜"""
    async with CoolapkClient() as client:
        raw = await client.get_board_feeds("hot", page)
    _output(_parse_feeds(raw))


@cli.command("boards")
def boards():
    """列出所有板块"""
    result = [
        {"id": bid, "title": title, "url": url}
        for bid, (title, url) in BOARD_URLS.items()
    ]
    _output(result)


@cli.command("board")
@click.argument("board_id")
@click.option("--page", default=1, type=int)
@async_command
async def board(board_id, page):
    """浏览板块（board_id 可用板块ID/page_name/url）"""
    async with CoolapkClient() as client:
        raw = await client.get_board_feeds(board_id, page)
    _output(_parse_feeds(raw))


@cli.command("secondhand")
@click.option("--brand", type=int, default=None, help="品牌ID（1005=苹果）")
@click.option("--page", default=1, type=int)
@async_command
async def secondhand(brand, page):
    """二手交易"""
    async with CoolapkClient() as client:
        raw = await client.get_secondhand_feeds(brand, page)
    _output(_parse_feeds(raw))


@cli.command("feed")
@click.argument("feed_id", type=int)
@click.option("--replies/--no-replies", default=True)
@click.option("--reply-page", default=1, type=int)
@click.option("--feed-type", default="feed",
              type=click.Choice(["feed", "trade", "feedArticle"]))
@async_command
async def feed(feed_id, replies, reply_page, feed_type):
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
            _output(_parse_feeds(raw))
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
            _output(_parse_feeds(raw))
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


# ---- 私信 ----


@cli.group("message")
def message():
    """私信管理"""
    pass


@message.command("list")
@click.option("--page", default=1, type=int)
@async_command
async def message_list(page):
    """私信会话列表"""
    async with CoolapkClient() as client:
        raw = await client.list_messages(page)
    if isinstance(raw, list):
        _output([ChatSessionModel.from_api(m) for m in raw if isinstance(m, dict)])
    else:
        _output(raw)


@message.command("chat")
@click.argument("ukey")
@click.option("--page", default=1, type=int)
@async_command
async def message_chat(ukey, page):
    """与某人的消息历史"""
    async with CoolapkClient() as client:
        raw = await client.list_chat(ukey, page)
    if isinstance(raw, list):
        _output([MessageModel.from_api(m) for m in raw if isinstance(m, dict)])
    else:
        _output(raw)


@message.command("read")
@click.argument("ukey")
@async_command
async def message_read(ukey):
    """标记私信已读"""
    async with CoolapkClient() as client:
        data = await client.read_message(ukey)
    _output(data)


@message.command("send")
@click.argument("uid", type=int)
@click.option("--message", "-m", required=True)
@click.option("--pic", default=None, help="图片 URL")
@async_command
async def message_send(uid, message, pic):
    """发送私信"""
    async with CoolapkClient() as client:
        data = await client.send_message(uid, message, pic)
    _output(data)


# ---- 交互（写操作，走 v3 token API） ----


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


@cli.command("post")
@click.option("--message", "-m", required=True, help="帖子正文")
@click.option("--pic", multiple=True, help="图片 URL（可多次指定）")
@async_command
async def post(message, pic):
    """发帖（动态）"""
    async with CoolapkClient() as client:
        data = await client.create_feed(message, list(pic) if pic else None)
    _output(data)


@cli.command("upload")
@click.argument("file_path")
@click.option("--dir", "upload_dir", default="feed", help="上传目录（feed/message）")
@async_command
async def upload(file_path, upload_dir):
    """上传图片，返回 URL"""
    async with CoolapkClient() as client:
        url = await client.upload_image(file_path, upload_dir)
    _output({"url": url})


# ---- 登录 ----


@cli.command("login")
@click.option("--cookie", help="Cookie 字符串 (uid=xxx;username=xxx;token=xxx)")
@click.option("--status", is_flag=True, help="查看登录状态")
@click.option("--adb", is_flag=True, help="从已连接的手机 ADB 自动提取 Cookie 登录")
@click.option("--sms", is_flag=True, help="短信验证码登录")
@click.option("--phone", help="手机号（SMS 登录用）")
@click.option("--captcha", help="图形验证码（SMS 发送验证码时需要）")
@click.option("--code", help="短信验证码（SMS 登录第二步）")
@click.option("--sessid", help="SESSID cookie（SMS 登录第二步，从第一步响应获取）")
@click.option("--validate-url", help="验证 URL（SMS 登录第二步，从第一步响应的 message 获取）")
@click.option("--captcha-file", default="/tmp/coolapk_captcha.jpg", help="图形验证码图片保存路径")
@async_command
async def login(cookie, status, adb, sms, phone, captcha, code, sessid, validate_url, captcha_file):
    """登录管理

    SMS 登录两步流程：
    第一步（发送验证码）：
      coolapk login --sms --phone <手机号> --captcha <图形验证码>
      → 验证码图片保存到 /tmp/coolapk_captcha.jpg，人工识别后重新带 --captcha 运行
      → 成功后返回 sessid 和 validate_url（message 字段）

    第二步（提交短信验证码）：
      coolapk login --sms --code <短信验证码> --sessid <第一步的sessid> --validate-url <第一步的message>
      → 成功后自动更新 config 的 uid/username/token
    """
    from coolapk_mcp.config import AppConfig

    config = AppConfig.load()

    # --status: 查看登录状态
    if status:
        _output({
            "logged_in": config.is_logged_in,
            "uid": config.uid,
            "username": config.username,
        })
        return

    # --adb: 从手机提取 Cookie
    if adb:
        cookie = _extract_cookie_from_adb()
        if not cookie:
            _output({"error": "未能从手机提取 Cookie，请确认手机已连接且酷安已登录"})
            sys.exit(1)

    # --sms: SMS 登录
    if sms:
        # 第二步：提交短信验证码
        if code and sessid and validate_url:
            async with CoolapkClient() as client:
                data = await client.login_sms(sessid, validate_url, code)
            # 成功则更新 config
            cookies = data.get("_cookies", {}) if isinstance(data, dict) else {}
            if cookies.get("uid") and cookies.get("token"):
                from urllib.parse import unquote
                config.uid = cookies["uid"]
                config.username = unquote(cookies.get("username", ""))
                config.token = cookies["token"]
                config.save()
                _output({
                    "status": "ok",
                    "uid": config.uid,
                    "username": config.username,
                    "message": data.get("message", ""),
                })
            else:
                _output(data)
            return

        # 第一步：发送验证码
        if phone and captcha:
            async with CoolapkClient() as client:
                if sessid:
                    # 复用之前的 session（验证码图片已在该 session 获取）
                    request_hash_to_use = validate_url or ""
                    # validate_url 在第一步用作 requestHash 传入（复用模式）
                    data = await client.send_sms_code(sessid, request_hash_to_use or "", phone, captcha)
                else:
                    # 新 session：获取登录页 SESSID + requestHash
                    sessid, request_hash = await client.get_sms_login_page()
                    data = await client.send_sms_code(sessid, request_hash, phone, captcha)
            if isinstance(data, dict):
                data["sessid"] = sessid
                _output(data)
            else:
                _output(data)
            return

        # 只传 phone 没传 captcha：获取验证码图片
        if phone and not captcha:
            async with CoolapkClient() as client:
                sessid, request_hash = await client.get_sms_login_page()
                captcha_bytes = await client.get_captcha_image(sessid)
            from pathlib import Path
            Path(captcha_file).write_bytes(captcha_bytes)
            _output({
                "step": "captcha_required",
                "sessid": sessid,
                "request_hash": request_hash,
                "captcha_file": captcha_file,
                "next": f"请识别 {captcha_file} 中的验证码，然后运行："
                        f" coolapk login --sms --phone {phone} --captcha <验证码> --sessid '{sessid}' --validate-url '{request_hash}'",
            })
            return

        _output({"error": "SMS 登录需要 --phone 参数。用法见 --help"})
        sys.exit(1)

    # --cookie: 手动 Cookie 登录
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
        return

    click.echo(json.dumps(
        {"error": "请使用 --cookie / --adb / --sms 登录，或 --status 查看状态"},
        ensure_ascii=False,
    ))
    sys.exit(1)


def _extract_cookie_from_adb() -> str | None:
    """从已连接的手机 ADB 提取酷安 Cookie

    前提：手机已 root，酷安已登录。
    从 /data/data/com.coolapk.market/shared_prefs/coolapk_preferences_v7.xml 提取
    uid/username/token。
    """
    import subprocess
    import re

    try:
        result = subprocess.run(
            ["adb", "shell", "su", "-c",
             "cat /data/data/com.coolapk.market/shared_prefs/coolapk_preferences_v7.xml"],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    xml = result.stdout
    if not xml:
        return None

    uid = re.search(r'<string name="uid">([^<]+)</string>', xml)
    username = re.search(r'<string name="username">([^<]+)</string>', xml)
    token = re.search(r'<string name="token">([^<]+)</string>', xml)

    if not (uid and username and token):
        return None

    return f"uid={uid.group(1)};username={username.group(1)};token={token.group(1)}"


if __name__ == "__main__":
    cli()