"""MCP Server — 酷安社区搜索工具"""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from coolapk_mcp.client import CoolapkClient, CoolapkError
from coolapk_mcp.models import (
    AppModel,
    FeedDetail,
    FeedModel,
    ReplyModel,
    TopicModel,
    UserModel,
)

mcp = FastMCP(
    "coolapk",
    instructions=(
        "酷安社区搜索工具。可搜索帖子、用户、应用、话题信息。"
        "主要用于获取社区内容和用户讨论信息。"
    ),
)

_client: CoolapkClient | None = None


def _get_client() -> CoolapkClient:
    global _client
    if _client is None:
        _client = CoolapkClient()
    return _client


def _dump(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json", exclude_defaults=True)
    return obj


def _json(data: Any) -> str:
    if data is None:
        return json.dumps({"error": "无数据"}, ensure_ascii=False)
    if isinstance(data, list):
        data = [_dump(item) for item in data]
    else:
        data = _dump(data)
    return json.dumps(data, ensure_ascii=False)


def _parse_feed_list(raw: Any) -> list[FeedModel]:
    if not isinstance(raw, list):
        return []
    return [FeedModel.from_api(f) for f in raw]


@mcp.tool()
async def coolapk_search(
    keyword: str, type: str = "feed", page: int = 1
) -> str:
    """搜索酷安社区内容。

    Args:
        keyword: 搜索关键词
        type: 搜索类型，可选 feed(帖子) user(用户) feedTopic(话题) app(应用)
        page: 页码
    """
    client = _get_client()
    data = await client.search(keyword, type, page)
    if not isinstance(data, list):
        return _json(data)
    results: list[Any] = []
    for item in data:
        if not isinstance(item, dict):
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
    return _json(results)


@mcp.tool()
async def coolapk_feed_detail(
    feed_id: int, with_replies: bool = True, reply_page: int = 1
) -> str:
    """获取酷安帖子的完整详情和回复。

    Args:
        feed_id: 帖子ID
        with_replies: 是否包含回复列表，默认是
        reply_page: 回复页码
    """
    client = _get_client()
    data = await client.get_feed_detail(feed_id)
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        return _json(data)
    reply_data = None
    if with_replies:
        reply_data = await client.get_feed_replies(feed_id, reply_page)
    detail = FeedDetail.from_api(
        data, reply_data if isinstance(reply_data, list) else None
    )
    return _json(detail)


@mcp.tool()
async def coolapk_user_profile(uid: int) -> str:
    """查看酷安用户资料。

    Args:
        uid: 用户UID
    """
    client = _get_client()
    data = await client.get_user_space(uid)
    if isinstance(data, list) and data:
        data = data[0]
    if isinstance(data, dict):
        return _json(UserModel.from_api(data))
    return _json(data)


@mcp.tool()
async def coolapk_user_feeds(uid: int, page: int = 1) -> str:
    """查看酷安用户发布的帖子。

    Args:
        uid: 用户UID
        page: 页码
    """
    client = _get_client()
    data = await client.get_user_feeds(uid, page)
    if isinstance(data, list):
        return _json(_parse_feed_list(data))
    return _json(data)


@mcp.tool()
async def coolapk_home(tab: str = "recommend", page: int = 1) -> str:
    """获取酷安首页动态。

    Args:
        tab: 类型，可选 recommend(推荐) hot(热门) latest(最新)
        page: 页码
    """
    client = _get_client()
    if tab == "hot":
        data = await client.get_hot_feeds(page)
    elif tab == "latest":
        data = await client.get_latest_feeds(page)
    else:
        data = await client.get_home_feeds(page)
    if isinstance(data, list):
        return _json(_parse_feed_list(data))
    return _json(data)


@mcp.tool()
async def coolapk_topic(tag: str, with_feeds: bool = False, page: int = 1) -> str:
    """查看酷安话题详情或话题下的帖子。

    Args:
        tag: 话题标签名
        with_feeds: 是否获取话题下的帖子列表
        page: 帖子页码
    """
    client = _get_client()
    result: dict[str, Any] = {}
    detail = await client.get_topic_detail(tag)
    if isinstance(detail, list) and detail:
        detail = detail[0]
    if isinstance(detail, dict):
        result["topic"] = TopicModel.from_api(detail)

    if with_feeds:
        feeds = await client.get_topic_feeds(tag, page)
        if isinstance(feeds, list):
            result["feeds"] = _parse_feed_list(feeds)
    return _json(result)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
