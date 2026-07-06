"""板块 URL 映射 — 21 个酷安板块

来源：skill references/api-endpoints.md
所有板块统一走 GET /v6/page/dataList?url=<page_name>&page=<n>
"""

from __future__ import annotations

# board_id → (title, url)
BOARD_URLS: dict[str, tuple[str, str]] = {
    "hot": ("热榜", "/page?url=V9_HOME_TAB_RANKING"),
    "news": ("快讯", "/page?url=V11_HOME_TAB_NEWS"),
    "headline": ("头条", "/main/headline"),
    "topic": ("话题", "/page?url=V9_HOME_TAB_TOPIC"),
    "video": ("视频", "/page?url=V9_HOME_TAB_SHIPIN"),
    "wenda": ("问答", "/page?url=V9_HOME_TAB_WENDA"),
    "xianliao": ("闲聊", "/page?url=V8_HUODONG_XIANLIAO_20210523"),
    "secondhand": ("二手交易", "#/feed/ershouList?dataListType=staggered"),
    "secondhand_apple": ("二手苹果", "#/feed/ershouList?brand=1005&dataListType=staggered"),
    "digital": ("数码", "/page?url=V10_DIGITAL_HOME"),
    "phone": ("手机", "/page?url=V10_CHANNEL_SJB"),
    "computer": ("电脑", "/page?url=V8_ZHUANTI_COMPUTER_20230413"),
    "system": ("系统ROM", "/page?url=V13_DIGITAL_ROM"),
    "sheying": ("摄影", "/page?url=V13_HOME_SHEYING"),
    "meihua": ("美化", "/page?url=V11_HOME_MEIHUA"),
    "kaixiang": ("开箱", "/page?url=V13_IOSHOME_OPENSHOW"),
    "car": ("汽车", "/page?url=V11_HOME_CAR"),
    "waishe": ("外设", "/page?url=V14_WAISHE"),
    "coolpic": ("酷图", "/page?url=V11_FIND_COOLPIC"),
    "goods": ("好物", "/page?url=V11_FIND_GOOD_GOODS_HOME"),
    "newphone": ("新机", "/page?url=V11_HOME_NEW"),
}


def resolve_board_url(board_id_or_url: str, board_urls: dict[str, tuple[str, str]] = BOARD_URLS) -> str:
    """解析板块 ID/page_name/url 为完整 url

    Args:
        board_id_or_url: 板块 ID（如 digital）、page_name（如 V10_DIGITAL_HOME）、或完整 url
        board_urls: 板块映射表

    Returns:
        可直接用于 /v6/page/dataList?url= 的 url 参数
    """
    # 1. 直接是 board_id
    if board_id_or_url in board_urls:
        return board_urls[board_id_or_url][1]
    # 2. 是 page_name（如 V10_DIGITAL_HOME）
    for _id, (_title, url) in board_urls.items():
        # 提取 url= 后面的 page_name
        if "url=" in url:
            page_name = url.split("url=", 1)[1]
            if board_id_or_url == page_name:
                return url
    # 3. 已经是完整 url（含 / 或 #）
    if "/" in board_id_or_url or board_id_or_url.startswith("#"):
        return board_id_or_url
    # 4. fallback：当作 page_name 直接拼
    return f"/page?url={board_id_or_url}"