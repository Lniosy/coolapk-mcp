"""HTTP 客户端 + API 封装 — 合并网络层和业务端点"""

import json
from typing import Any
from urllib.parse import quote

import httpx

from coolapk_mcp.auth.token_v3 import DEFAULT_APP_VERSION, DEFAULT_VERSION_CODE, generate_token_v3
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
        """组装请求头，每次请求重新生成 X-App-Token（v3 算法）"""
        token, _ = generate_token_v3(self.config.device_code)
        return {
            "X-Sdk-Int": "35",
            "X-Sdk-Locale": "zh-CN",
            "X-App-Mode": "universal",
            "X-App-Channel": "coolapk",
            "X-App-Id": "com.coolapk.market",
            "X-App-Device": self.config.device_code,
            "X-App-Version": DEFAULT_APP_VERSION,
            "X-App-Code": str(DEFAULT_VERSION_CODE),
            "X-Api-Version": "16",
            "X-App-Supported": str(DEFAULT_VERSION_CODE),
            "X-Dark-Mode": "0",
            "X-Requested-With": "XMLHttpRequest",
            "X-App-Token": token,
            "User-Agent": (
                "Dalvik/2.1.0 (Linux; U; Android 16; 23113RKC6C Build/AQ3A.250226.002) "
                "(#Build; Redmi; 23113RKC6C; AQ3A.250226.002; HyperOS_3.0; 3.0.1.0) "
                f"+CoolMarket/{DEFAULT_APP_VERSION}-{DEFAULT_VERSION_CODE}-universal"
            ),
        }

    def _get_cookie_header(self) -> str | None:
        """返回 Cookie 字符串。直接拼字符串避免 httpx cookies 参数对中文 username 的编码问题。"""
        if not self.config.is_logged_in:
            return None
        return f"uid={self.config.uid}; username={quote(self.config.username, safe='')}; token={self.config.token}"

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        """统一请求方法"""
        url = f"{self.config.api_base}{path}"
        headers = self._build_headers()
        cookie = self._get_cookie_header()
        if cookie:
            headers["Cookie"] = cookie

        try:
            resp = await self._client.request(
                method, url, headers=headers, **kwargs
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

    async def post_multipart(
        self, path: str, fields: dict[str, str] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
    ) -> Any:
        """multipart/form-data POST。files 格式: {name: (filename, content, content_type)}"""
        return await self._request(
            "POST", path, data=fields or {}, files=files or {}
        )

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

    async def get_main_feeds(self, page: int = 1) -> list[dict]:
        """首页推荐（main/indexV8）"""
        return await self.get("/v6/main/indexV8", {"page": page})

    async def get_board_feeds(
        self, board_id_or_url: str, page: int = 1
    ) -> list[dict]:
        """通用板块浏览

        Args:
            board_id_or_url: 板块 ID（如 digital）、page_name（如 V10_DIGITAL_HOME）、或完整 url
            page: 页码
        """
        from coolapk_mcp.boards import BOARD_URLS, resolve_board_url

        url = resolve_board_url(board_id_or_url, BOARD_URLS)
        return await self.get("/v6/page/dataList", {"url": url, "page": page})

    async def get_secondhand_feeds(
        self, brand: int | None = None, page: int = 1
    ) -> list[dict]:
        """二手交易帖子

        Args:
            brand: 品牌ID（1005=苹果），None 则全部二手
            page: 页码
        """
        if brand:
            url = f"#/feed/ershouList?brand={brand}&dataListType=staggered"
        else:
            url = "#/feed/ershouList?dataListType=staggered"
        return await self.get("/v6/page/dataList", {"url": url, "page": page})

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

    # ---- 发帖 ----

    async def create_feed(self, message: str, pic_urls: list[str] | None = None) -> Any:
        """发帖（动态）

        Args:
            message: 帖子正文
            pic_urls: 已上传的图片 URL 列表（通过 upload_image 获取）

        Returns:
            API 返回的 feed 数据
        """
        fields = {
            "message": message,
            "type": "feed",
            "is_html_article": "0",
            "pic": ",".join(pic_urls) if pic_urls else "",
        }
        return await self.post_multipart("/v6/feed/createFeed", fields=fields)

    async def upload_image(
        self, file_path: str, upload_dir: str = "feed"
    ) -> str:
        """上传图片到酷安服务器，返回图片 URL。

        Args:
            file_path: 本地图片文件路径
            upload_dir: 上传目录（feed/message 等）

        Returns:
            图片 URL 字符串
        """
        from pathlib import Path

        p = Path(file_path)
        if not p.exists():
            raise CoolapkError(f"图片文件不存在: {file_path}")

        content = p.read_bytes()
        content_type = "image/jpeg"
        if p.suffix.lower() == ".png":
            content_type = "image/png"
        elif p.suffix.lower() == ".gif":
            content_type = "image/gif"
        elif p.suffix.lower() == ".webp":
            content_type = "image/webp"

        files = {
            "picFile": (p.name, content, content_type),
        }
        result = await self.post_multipart(
            f"/v6/feed/uploadImage?fieldName=picFile&uploadDir={upload_dir}",
            files=files,
        )
        # 返回结构通常是 {"url": "..."} 或字符串 URL
        if isinstance(result, dict):
            return result.get("url") or result.get("picUrl") or result.get("data", "")
        if isinstance(result, str):
            return result
        return str(result) if result else ""

    # ---- 私信 ----

    async def send_message(
        self, uid: int, text: str, pic_url: str | None = None
    ) -> Any:
        """发送私信

        Args:
            uid: 目标用户 UID
            text: 消息文本
            pic_url: 可选图片 URL（通过 upload_image 上传到 message 目录获取）
        """
        fields = {"message": text}
        if pic_url:
            fields["message_pic"] = pic_url
        return await self.post_multipart(
            f"/v6/message/send?uid={uid}", fields=fields
        )

    async def list_messages(self, page: int = 1) -> list[dict]:
        """私信会话列表"""
        return await self.get(f"/v6/message/list?page={page}")

    async def list_chat(self, ukey: str, page: int = 1) -> list[dict]:
        """与某人的消息历史

        Args:
            ukey: 会话对方的 ukey（从 list_messages 获取）
        """
        return await self.get(f"/v6/message/chat?ukey={ukey}&page={page}")

    async def read_message(self, ukey: str) -> Any:
        """标记私信已读"""
        return await self.get(f"/v6/message/read?ukey={ukey}")

    # ---- 验证码 ----

    async def get_captcha_image(self, width: int = 180, height: int = 60) -> str:
        """获取图形验证码图片 URL（触发风控时使用）

        Returns:
            验证码图片 URL
        """
        import time as _time

        t = int(_time.time() * 1000)
        return f"{self.config.api_base}/v6/account/captchaImage?time={t}&w={width}&h={height}"

    async def request_validate(self, captcha: str, **extra) -> Any:
        """提交图形验证码校验（风控解锁）

        Args:
            captcha: 用户输入的验证码
            **extra: 额外参数（视风控场景而定）
        """
        data = {"captcha": captcha, **extra}
        return await self.post("/v6/account/requestValidate", data)

    # ---- SMS 登录（走 account.coolapk.com 网页登录流程） ----

    async def _auth_request(
        self, method: str, path: str, sessid: str = "",
        data: dict | None = None, referer: str = "https://account.coolapk.com/auth/login?type=mobile",
    ) -> httpx.Response:
        """account.coolapk.com 的请求（模拟酷安 APP WebView）

        关键点：
        - User-Agent 用真实 Android WebView UA（Chrome 149）
        - X-Requested-With: com.coolapk.market 标识 APP
        - Cookie 带 DID/oaid/AppSupported 等 APP 设备标识（服务端校验是否来自 APP）
        - 不自动跟随重定向（follow_redirects=False），调用方需自行处理 302
        """
        url = f"https://account.coolapk.com{path}"
        # 组装 Cookie：SESSID + APP 设备标识
        cookie_parts = []
        if sessid:
            cookie_parts.append(sessid)
        cookie_parts.append("forward=https://www.coolapk.com")
        cookie_parts.append("AppSupported=2604201")
        cookie_parts.append("darkMode=0")
        cookie_parts.append("displayVersion=v14")
        # DID 和 oaid 是 APP 设备标识，validateLogin 端点用这些判断是否来自 APP
        # 这些值从手机 ADB 提取或用任意值（服务端不严格校验具体值，只检查字段存在）
        cookie_parts.append("DID=coolapk_mcp_default_did")
        cookie_parts.append("oaid=coolapk_mcp_default_oaid")
        cookie_str = "; ".join(cookie_parts)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 16; 23113RKC6C Build/BP2A.250605.031.A3; wv) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
                "Chrome/149.0.7827.91 Mobile Safari/537.36"
            ),
            "X-Requested-With": "com.coolapk.market",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": referer,
            "sec-ch-ua": '"Android WebView";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "Cookie": cookie_str,
        }
        if method == "POST":
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            headers["Origin"] = "https://account.coolapk.com"
            headers["X-Requested-With"] = "XMLHttpRequest"
            headers["Accept"] = "*/*"
            headers["Sec-Fetch-Site"] = "same-origin"
            headers["Sec-Fetch-Mode"] = "cors"
            headers["Sec-Fetch-Dest"] = "empty"
        else:
            headers["Upgrade-Insecure-Requests"] = "1"
            headers["Sec-Fetch-Site"] = "none"
            headers["Sec-Fetch-Mode"] = "navigate"
            headers["Sec-Fetch-User"] = "?1"
            headers["Sec-Fetch-Dest"] = "document"
        # 不跟随重定向，让调用方处理 302
        return await self._client.request(method, url, headers=headers, data=data, follow_redirects=False)

    async def get_sms_login_page(self) -> tuple[str, str]:
        """获取 SMS 登录页，返回 (sessid_cookie, request_hash)

        流程：
        1. GET /auth/login?type=mobile 获取 HTML 和 SESSID cookie
        2. 从 HTML 解析 requestHash
        """
        import re

        resp = await self._auth_request("GET", "/auth/login?type=mobile")
        html = resp.text
        # 提取 SESSID
        sessid = ""
        for cookie in resp.headers.get_list("set-cookie"):
            if "SESSID=" in cookie:
                sessid = cookie.split(";")[0]
                break
        # 提取 requestHash
        m = re.search(r"requestHash[:\s]+['\"]([^'\"]+)['\"]", html)
        request_hash = m.group(1) if m else ""
        if not request_hash:
            raise CoolapkError("无法从登录页解析 requestHash")
        return sessid, request_hash

    async def get_captcha_image(self, sessid: str) -> bytes:
        """获取图形验证码图片 bytes

        Args:
            sessid: 从 get_sms_login_page 获取的 SESSID cookie
        """
        import time as _time

        ts = int(_time.time() * 1000)
        resp = await self._auth_request(
            "GET", f"/auth/showCaptchaImage?{ts}", sessid=sessid,
            referer="https://account.coolapk.com/auth/loginByCoolapk",
        )
        return resp.content

    async def send_sms_code(
        self, sessid: str, request_hash: str, phone: str, captcha: str, country: int = 86,
    ) -> dict:
        """发送短信验证码（POST /auth/login?type=mobile）

        这是 SMS 登录的第一步。服务端验证图形验证码后发送短信到手机。

        Args:
            sessid: SESSID cookie
            request_hash: 从登录页获取的 requestHash
            phone: 手机号
            captcha: 图形验证码（用户识别 get_captcha_image 返回的图片后输入）
            country: 国家码，默认 86

        Returns:
            API 响应 dict。
            - HTTP 302：验证码正确，短信已发送。Location 头是验证码输入页 URL。
              返回 {"status": 1, "validate_url": "<Location>", "message": "短信验证码已发送"}
            - HTTP 200 + JSON：验证码错误或频率限制。看 message 字段。
            - status==-1 表示需要图形验证码。
        """
        import time as _time

        data = {
            "submit": 1,
            "requestHash": request_hash,
            "country": country,
            "mobile": phone,
            "captcha": captcha,
            "randomNumber": f"{int(_time.time()*1000)}{int(_time.time()%1000)}",
            # 网易易盾反机器人 token：nscode=200 是固定成功码，
            # nstoken 用任意值即可通过服务端 APP 环境检测（实测验证）
            "nscode": "200",
            "nstoken": "coolapk_mcp_python_client",
        }
        resp = await self._auth_request("POST", "/auth/login?type=mobile", sessid=sessid, data=data)

        # 302 重定向 = 验证码正确，短信已发送
        if resp.status_code == 302:
            location = resp.headers.get("location", "")
            return {
                "status": 1,
                "message": "短信验证码已发送",
                "validate_url": location,
                "sessid": sessid,
            }

        # 200 JSON 响应
        try:
            result = resp.json()
        except Exception:
            text = resp.text[:500] if resp.text else ""
            raise CoolapkError(f"发送验证码响应解析失败: HTTP {resp.status_code}, body={text}")
        return result

    async def login_sms(self, sessid: str, validate_url: str, code: str) -> dict:
        """提交短信验证码完成登录

        这是 SMS 登录的第二步。send_sms_code 成功后返回的 validate_url 是
        `/auth/validateLogin?key=<token>` 格式。

        流程：
        1. GET validate_url 获取验证码输入页 HTML + 新的 requestHash
        2. POST validate_url 提交 code + type=code + requestHash

        Args:
            sessid: SESSID cookie（必须与 send_sms_code 用同一个 session）
            validate_url: send_sms_code 成功返回的 validate_url
            code: 用户收到的短信验证码

        Returns:
            API 响应 dict。成功后 Set-Cookie 里会有 uid/username/token。
        """
        import re
        import time as _time

        # validate_url 是路径格式 /auth/validateLogin?key=xxx
        path = validate_url
        if validate_url.startswith("https://"):
            path = validate_url
            if validate_url.startswith("https://"):
                # 去掉 host 部分
                for host in ("account.coolapk.com", "www.coolapk.com"):
                    if host in validate_url:
                        path = validate_url.split(host, 1)[-1]
                        break
        elif not validate_url.startswith("/"):
            path = f"/{validate_url}"

        # 1. GET validate 页面获取新的 requestHash
        resp = await self._auth_request("GET", path, sessid=sessid)
        html = resp.text
        m = re.search(r"requestHash[:\s]+['\"]([^'\"]+)['\"]", html)
        request_hash = m.group(1) if m else ""

        # 2. POST 提交验证码
        data = {
            "submit": 1,
            "requestHash": request_hash,
            "code": code,
            "type": "code",
            "randomNumber": f"{int(_time.time()*1000)}{int(_time.time()%1000)}",
            # 网易易盾反机器人 token（同 send_sms_code）
            "nscode": "200",
            "nstoken": "coolapk_mcp_python_client",
        }
        resp = await self._auth_request(
            "POST", path, sessid=sessid, data=data,
            referer=f"https://account.coolapk.com{path}",
        )

        # 检查 302 重定向（登录成功）
        if resp.status_code == 302:
            location = resp.headers.get("location", "")
            cookies = {}
            for cookie in resp.headers.get_list("set-cookie"):
                for name in ("uid", "username", "token"):
                    if cookie.startswith(f"{name}="):
                        val = cookie.split(";")[0].split("=", 1)[1]
                        if val and val != "deleted":
                            cookies[name] = val
            return {
                "status": 1,
                "message": "登录成功",
                "redirect": location,
                "_cookies": cookies,
            }

        try:
            result = resp.json()
        except Exception:
            text = resp.text[:500] if resp.text else ""
            raise CoolapkError(f"短信验证码登录响应解析失败: HTTP {resp.status_code}, body={text}")

        # 从 Set-Cookie 提取 uid/username/token
        cookies = {}
        for cookie in resp.headers.get_list("set-cookie"):
            for name in ("uid", "username", "token"):
                if cookie.startswith(f"{name}="):
                    val = cookie.split(";")[0].split("=", 1)[1]
                    if val and val != "deleted":
                        cookies[name] = val
        result["_cookies"] = cookies
        return result

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()
