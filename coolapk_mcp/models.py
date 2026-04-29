"""数据模型 — 精简字段，exclude_defaults 节省 token"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, field_validator, model_validator


def _strip_html(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def _format_time(timestamp: int | float) -> str:
    if not timestamp:
        return ""
    try:
        dt = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError):
        return ""


def _extract_pics(pic_arr: list[str] | str) -> list[str]:
    if isinstance(pic_arr, str):
        if not pic_arr:
            return []
        import json

        try:
            pic_arr = json.loads(pic_arr)
        except (json.JSONDecodeError, TypeError):
            return [pic_arr] if pic_arr else []
    if isinstance(pic_arr, list):
        return [p for p in pic_arr if isinstance(p, str) and p]
    return []


def _pic_count(raw: Any) -> int:
    pics = raw if isinstance(raw, list) else _extract_pics(raw)
    return len(pics) if pics else 0


class FeedModel(BaseModel):
    id: int = 0
    title: str = ""
    message: str = Field(exclude=True, default="")  # HTML，仅内部用
    content: str = ""  # 纯文本，由 model_validator 从 message 生成
    feed_type: str = Field(alias="feedType", default="feed")
    username: str = ""
    uid: int = 0
    user_level: int = Field(default=0)
    like_num: int = Field(alias="likenum", default=0)
    reply_num: int = Field(alias="replynum", default=0)
    forward_num: int = Field(alias="forwardnum", default=0)
    dateline: str = ""
    device: str = Field(alias="deviceTitle", default="")
    ip_location: str = Field(alias="ipLocation", default="")
    image_count: int = 0

    @model_validator(mode="after")
    def _generate_content(self) -> FeedModel:
        if not self.content and self.message:
            self.content = _strip_html(self.message)
        return self

    @field_validator("dateline", mode="before")
    @classmethod
    def _format_dateline(cls, v: Any) -> str:
        if isinstance(v, str) and v.lstrip("-").isdigit():
            v = int(v)
        if isinstance(v, (int, float)) and v:
            return _format_time(v)
        return str(v) if v else ""

    @classmethod
    def from_api(cls, data: dict) -> FeedModel:
        user_info = data.get("userInfo") or {}
        pics = data.get("picArr") or data.get("pic") or []
        return cls(
            id=data.get("id", 0),
            title=data.get("messageTitle", "") or data.get("title", ""),
            message=data.get("message", ""),
            feedType=data.get("feedType", "feed"),
            username=user_info.get("username", ""),
            uid=user_info.get("uid", 0),
            user_level=user_info.get("level", 0),
            likenum=data.get("likenum", 0),
            replynum=data.get("replynum", 0),
            forwardnum=data.get("forwardnum", 0),
            dateline=data.get("dateline", 0),
            deviceTitle=data.get("deviceTitle", ""),
            ipLocation=data.get("ipLocation", ""),
            image_count=_pic_count(pics),
        )


class FeedDetail(FeedModel):
    read_num: int = Field(alias="readNum", default=0)
    source_feed: FeedModel | None = None
    replies: list[ReplyModel] = Field(default_factory=list)
    reply_count: int = 0

    @classmethod
    def from_api(
        cls, data: dict, replies: list[dict] | None = None
    ) -> FeedDetail:
        user_info = data.get("userInfo") or {}
        pics = data.get("picArr") or data.get("pic") or []
        source = data.get("forwardSourceFeed")
        source_feed = FeedModel.from_api(source) if source else None
        reply_rows = replies or []
        parsed_replies = [ReplyModel.from_api(r) for r in reply_rows]
        return cls(
            id=data.get("id", 0),
            title=data.get("messageTitle", "") or data.get("title", ""),
            message=data.get("message", ""),
            feedType=data.get("feedType", "feed"),
            username=user_info.get("username", ""),
            uid=user_info.get("uid", 0),
            user_level=user_info.get("level", 0),
            likenum=data.get("likenum", 0),
            replynum=data.get("replynum", 0),
            forwardnum=data.get("forwardnum", 0),
            dateline=data.get("dateline", 0),
            deviceTitle=data.get("deviceTitle", ""),
            ipLocation=data.get("ipLocation", ""),
            image_count=_pic_count(pics),
            readNum=data.get("readNum", 0),
            source_feed=source_feed,
            replies=parsed_replies,
            reply_count=data.get("replyRowsCount", 0) or data.get("replynum", 0),
        )


class ReplyModel(BaseModel):
    id: int = 0
    message: str = Field(exclude=True, default="")
    content: str = ""
    username: str = ""
    uid: int = 0
    like_num: int = Field(alias="likenum", default=0)
    dateline: str = ""
    is_author: bool = Field(alias="isFeedAuthor", default=False)
    image_count: int = 0

    @model_validator(mode="after")
    def _generate_content(self) -> ReplyModel:
        if not self.content and self.message:
            self.content = _strip_html(self.message)
        return self

    @field_validator("dateline", mode="before")
    @classmethod
    def _format_dateline(cls, v: Any) -> str:
        if isinstance(v, str) and v.lstrip("-").isdigit():
            v = int(v)
        if isinstance(v, (int, float)) and v:
            return _format_time(v)
        return str(v) if v else ""

    @classmethod
    def from_api(cls, data: dict) -> ReplyModel:
        user_info = data.get("userInfo") or {}
        pics = data.get("picArr") or data.get("pic") or []
        return cls(
            id=data.get("id", 0),
            message=data.get("message", ""),
            username=user_info.get("username", ""),
            uid=user_info.get("uid", 0),
            likenum=data.get("likenum", 0),
            dateline=data.get("dateline", 0),
            isFeedAuthor=bool(data.get("isFeedAuthor", 0)),
            image_count=_pic_count(pics),
        )


class UserModel(BaseModel):
    uid: int = 0
    username: str = ""
    bio: str = ""
    level: int = 0
    fans_num: int = Field(alias="fans", default=0)
    follow_num: int = Field(alias="follow", default=0)
    feed_num: int = Field(alias="feed", default=0)
    verify_title: str = Field(alias="verifyTitle", default="")
    reg_date: str = Field(alias="regdate", default="")
    city: str = ""
    gender: str = ""

    @field_validator("reg_date", mode="before")
    @classmethod
    def _format_regdate(cls, v: Any) -> str:
        if isinstance(v, str) and v.lstrip("-").isdigit():
            v = int(v)
        if isinstance(v, (int, float)) and v:
            return _format_time(v)
        return str(v) if v else ""

    @field_validator("gender", mode="before")
    @classmethod
    def _format_gender(cls, v: Any) -> str:
        mapping = {1: "男", 2: "女"}
        if isinstance(v, int):
            return mapping.get(v, "")
        return str(v) if v else ""

    @classmethod
    def from_api(cls, data: dict) -> UserModel:
        return cls(
            uid=data.get("uid", 0),
            username=data.get("username", ""),
            bio=data.get("bio", ""),
            level=data.get("level", 0),
            fans=data.get("fans", 0),
            follow=data.get("follow", 0),
            feed=data.get("feed", 0),
            verifyTitle=data.get("verifyTitle", ""),
            regdate=data.get("regdate", 0),
            city=data.get("city", ""),
            gender=data.get("gender", 0),
        )


class TopicModel(BaseModel):
    id: int = 0
    title: str = ""
    tag: str = ""
    follow_num: int = Field(alias="follownum", default=0)
    comment_num: int = Field(alias="commentnum", default=0)
    description: str = ""

    @classmethod
    def from_api(cls, data: dict) -> TopicModel:
        return cls(
            id=data.get("id", 0),
            title=data.get("title", ""),
            tag=data.get("tag", "") or data.get("title", ""),
            follownum=data.get("follownum", 0) or data.get("follow_num", 0),
            commentnum=data.get("commentnum", 0)
            or data.get("newsnum", 0)
            or data.get("rating_total_num", 0),
            description=data.get("description", "")
            or data.get("newtitle", "")
            or data.get("username", ""),
        )


class AppModel(BaseModel):
    id: int = 0
    title: str = ""
    package_name: str = Field(alias="pkgname", default="")
    description: str = ""
    follow_num: int = Field(alias="followNum", default=0)
    download_num: int = Field(alias="downloadCount", default=0)
    version: str = Field(alias="versionName", default="")

    @classmethod
    def from_api(cls, data: dict) -> AppModel:
        return cls(
            id=data.get("id", 0),
            title=data.get("title", ""),
            pkgname=data.get("pkgname", ""),
            description=data.get("description", "") or data.get("keywords", ""),
            followNum=data.get("followNum", 0),
            downloadCount=data.get("downloadCount", 0) or data.get("downloadnum", 0),
            versionName=data.get("versionName", ""),
        )
