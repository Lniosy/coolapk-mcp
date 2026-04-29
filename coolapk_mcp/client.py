"""HTTP 客户端 + API 封装 — 合并网络层和业务端点"""

import json
from typing import Any

import httpx

from coolapk_mcp.auth.token import generate_token
from coolapk_mcp.config import AppConfig


class CoolapkError(Exception):
    """API 业务错误"""

    def __init__(self, message: str, error_code: int = -1):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class CoolapkClient:
    """酷安 API 客户端"""

    BASE_URL = "https://api.coolapk.com"

    def __init__(self, config: AppConfig | None = None):
        self.config = config or AppConfig.load()
        self._client = httpx.AsyncClient(timeout=30.0)

    def _build_headers(self) -> dict[str, str]:
        """组装请求头，每次请求重新生成 X-App-Token"""
        return {
            "X-Sdk-Int": "33",
            "X-Sdk-Locale": "zh-CN",
            "X-App-Mode": "universal",
            "X-App-Channel": "coolapk",
            "X-App-Id": "com.coolapk.market",
            "X-App-Device": self.config.device_code,
            "X-App-Version": "13.4.1",
            "X-App-Code": "2312121",
            "X-Api-Version": "13",
            "X-Api-Supported": "2312121",
            "X-Dark-Mode": "0",
            "X-Requested-With": "XMLHttpRequest",
            "X-App-Token": generate_token(self.config.device_code),
            "User-Agent": (
                "Dalvik/2.1.0 (Windows NT 10.0; Win64; x64; WebView/3.0) "
                "(#Build; Apple; Mac; Apple_Mac; 10.15.7) "
                "+CoolMarket/13.4.1-2312121-universal"
            ),
        }

    def _get_cookies(self) -> dict[str, str] | None:
        if not self.config.is_logged_in:
            return None
        return self.config.get_cookies()

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        """统一请求方法"""
        url = f"{self.config.api_base}{path}"
        headers = self._build_headers()
        cookies = self._get_cookies()

        try:
            resp = await self._client.request(
                method, url, headers=headers, cookies=cookies, **kwargs
            )
            resp.raise_for_status()
        except httpx.TimeoutException:
            raise CoolapkError("请求超时")
        except httpx.ConnectError:
            raise CoolapkError("无法连接服务器")
        except httpx.HTTPStatusError as e:
            raise CoolapkError(f"HTTP {e.response.status_code}")

        try:
            result = resp.json()
        except json.JSONDecodeError:
            raise CoolapkError("响应解析失败")

        # 检查业务错误
        if "data" not in result and "message" in result:
            error_code = result.get("error", -1)
            message = result.get("message", "未知错误")
            if isinstance(error_code, str):
                error_code = int(error_code) if error_code.lstrip("-").isdigit() else -1
            raise CoolapkError(message, error_code)

        return result.get("data")

    async def get(self, path: str, params: dict | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, data: dict | None = None) -> Any:
        return await self._request("POST", path, data=data or {})

    # ---- 浏览 ----

    async def get_home_feeds(self, page: int = 1) -> list[dict]:
        """首页推荐动态"""
        return await self.get(
            "/v6/page/dataList",
            {"url": "/page?url=V9_HOME_TAB_FOLLOW", "page": page},
        )

    async def get_hot_feeds(self, page: int = 1) -> list[dict]:
        """热门动态"""
        return await self.get(
            "/v6/page/dataList",
            {"url": "/feed/hotList", "page": page},
        )

    async def get_latest_feeds(self, page: int = 1) -> list[dict]:
        """最新动态"""
        return await self.get(
            "/v6/page/dataList",
            {"url": "/feed/newestList", "page": page},
        )

    # ---- 动态 ----

    async def get_feed_detail(self, feed_id: int) -> dict | list:
        """动态详情"""
        return await self.get(f"/v6/feed/detail?id={feed_id}")

    async def get_feed_replies(
        self, feed_id: int, page: int = 1, list_type: str = "lastupdate_desc"
    ) -> list[dict]:
        """动态回复列表"""
        return await self.get(
            f"/v6/feed/replyList?id={feed_id}&listType={list_type}"
            f"&page={page}&discussMode=1&feedType=feed"
        )

    async def get_hot_replies(self, feed_id: int, page: int = 1) -> list[dict]:
        """热门回复"""
        return await self.get(
            f"/v6/feed/hotReplyList?id={feed_id}&page={page}&discussMode=1"
        )

    # ---- 搜索 ----

    async def search(
        self, keyword: str, search_type: str = "feed", page: int = 1
    ) -> list[dict]:
        """通用搜索
        search_type: feed / user / feedTopic / app
        """
        return await self.get(
            "/v6/search",
            {
                "type": search_type,
                "searchValue": keyword,
                "page": page,
                "showAnonymous": "-1",
            },
        )

    async def search_feeds(
        self,
        keyword: str,
        feed_type: str = "feed",
        sort: str = "default",
        page: int = 1,
    ) -> list[dict]:
        """搜索动态"""
        return await self.get(
            "/v6/search",
            {
                "type": "feed",
                "feedType": feed_type,
                "sort": sort,
                "searchValue": keyword,
                "page": page,
                "showAnonymous": "-1",
            },
        )

    # ---- 用户 ----

    async def get_user_space(self, uid: int) -> dict | list:
        """用户空间"""
        return await self.get(f"/v6/user/space?uid={uid}")

    async def get_user_profile(self, uid: int) -> dict | list:
        """用户资料"""
        return await self.get(f"/v6/user/profile?uid={uid}")

    async def get_user_feeds(
        self, uid: int, page: int = 1, feed_type: str = "feed"
    ) -> list[dict]:
        """用户动态列表"""
        return await self.get(
            f"/v6/user/{feed_type}List?uid={uid}&page={page}&isIncludeTop=1"
        )

    # ---- 话题 ----

    async def get_topic_detail(self, tag: str) -> dict | list:
        """话题详情"""
        return await self.get(f"/v6/topic/newTagDetail?tag={tag}")

    async def get_topic_feeds(self, tag: str, page: int = 1) -> list[dict]:
        """话题下的帖子"""
        return await self.get(
            f"/v6/topic/tagFeedList?tag={tag}&page={page}"
        )

    # ---- 应用 ----

    async def get_app_detail(self, package_name: str) -> dict | list:
        """应用详情"""
        return await self.get(f"/v6/apk/detail?id={package_name}")

    # ---- 通知 ----

    async def get_notification_count(self) -> dict | list:
        """未读通知计数"""
        return await self.get("/v6/notification/checkCount")

    async def get_notifications(
        self, ntype: str, page: int = 1
    ) -> list[dict]:
        """通知列表
        ntype: atMeMeFeed / atComment / comment / feedLike / contactsFollow / message
        """
        return await self.get(f"/v6/notification/{ntype}?page={page}")

    # ---- 交互（需登录） ----

    async def like_feed(self, feed_id: int) -> Any:
        return await self.post(f"/v6/feed/like?id={feed_id}")

    async def unlike_feed(self, feed_id: int) -> Any:
        return await self.post(f"/v6/feed/unlike?id={feed_id}")

    async def like_reply(self, reply_id: int) -> Any:
        return await self.post(f"/v6/feed/likeReply?id={reply_id}")

    async def reply_feed(self, feed_id: int, message: str) -> Any:
        return await self.post(
            f"/v6/feed/reply?id={feed_id}&type=feed",
            data={"message": message},
        )

    async def reply_reply(self, reply_id: int, message: str) -> Any:
        return await self.post(
            f"/v6/feed/reply?id={reply_id}&type=reply",
            data={"message": message},
        )

    async def follow_user(self, uid: int) -> Any:
        return await self.post(f"/v6/user/follow?uid={uid}")

    async def unfollow_user(self, uid: int) -> Any:
        return await self.post(f"/v6/user/unfollow?uid={uid}")

    async def check_login(self) -> Any:
        return await self.get("/v6/account/checkLoginInfo")

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()
