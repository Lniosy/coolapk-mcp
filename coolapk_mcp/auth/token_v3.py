"""Token V3 生成 — 酷安 v16.x 的 X-App-Token 算法

替代旧版 token.py 的 V2 实现。V3 与 V2 完全不同：
- V2: bcrypt cost=10, salt=base64(ts)/md5hash 截 24 字符 + "u"
- V3: bcrypt cost=10, salt=base64(hex(ts)/md5(plain))[:22] 末位偏移 -5

V3 的 salt 第二段依赖从 libauth.so 解密出的 blob（见 libauth.py），
按 ((ts + version_code) % 100) * 4 + 0x80 索引切片得到 segment。

算法来源：https://github.com/qiuyurs/coolApkAPI
验证：2026-07-06 酷安 v16.2.0 / versionCode=2604201 实测，读+写操作均成功。

已知坑：Python bcrypt 对部分 V3 盐会抛 `Invalid salt`，
用时间戳前探（+0..MAX_AHEAD 秒）规避。
"""

from __future__ import annotations

import base64
import hashlib
import time

import bcrypt

from coolapk_mcp.auth.libauth import get_blob

# 标准 base64 字母表（用于 salt 末位偏移）
_STD_B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

# 当前酷安版本参数（v16.2.0）
DEFAULT_VERSION_CODE = 2604201
DEFAULT_APP_VERSION = "16.2.0"
DEFAULT_PACKAGE = "com.coolapk.market"

# 时间戳前探窗口（解决 bcrypt Invalid salt 问题）
_MAX_AHEAD = 15

# salt 末位偏移量
_SALT_LAST_CHAR_SHIFT = -5

# bcrypt cost
_BCRYPT_COST = 10


def _shift_last_char(s: str, shift: int) -> str:
    """把字符串最后一位在标准 base64 字母表里偏移 shift 位（mod 64）"""
    idx = _STD_B64.index(s[-1])
    return s[:-1] + _STD_B64[(idx + shift) % 64]


def _generate_token_at(
    device: str,
    ts: int,
    version_code: int = DEFAULT_VERSION_CODE,
    package: str = DEFAULT_PACKAGE,
) -> str:
    """在指定时间戳生成 v3 token。

    Args:
        device: X-App-Device 值
        ts: Unix 时间戳（秒）
        version_code: App versionCode
        package: 包名

    Returns:
        v3 开头的 token 字符串

    Raises:
        ValueError: bcrypt 报 Invalid salt（调用方应换时间戳重试）
    """
    blob = get_blob()

    # 索引切片
    idx = ((ts + version_code) % 100) * 4 + 0x80
    if idx + 0x80 > len(blob):
        raise RuntimeError(
            f"blob 索引越界: idx={idx}, blob_len={len(blob)}. "
            "可能是 version_code 与 blob 不匹配，请重新提取 libauth.so。"
        )
    chunk = blob[idx : idx + 0x80]
    segment = base64.b64decode(chunk)

    # 组装 plain（字节拼接）
    md5_device = hashlib.md5(device.encode("utf-8")).hexdigest().encode("ascii")
    plain = (
        package.encode("utf-8")
        + b"&"
        + segment
        + b"&"
        + md5_device
        + b"&"
        + str(ts).encode("ascii")
        + b"&"
        + str(version_code).encode("ascii")
    )

    # 密码串
    pw = hashlib.md5(base64.b64encode(plain)).hexdigest().encode("ascii")

    # 盐来源
    salt_src = (
        base64.b64encode(f"{ts:x}/{hashlib.md5(plain).hexdigest()}".encode("ascii"))
        .decode("ascii")
        .rstrip("=")
    )
    salt22 = _shift_last_char(salt_src[:22], _SALT_LAST_CHAR_SHIFT)
    setting = f"$2y${_BCRYPT_COST}${salt22}".encode("ascii")

    # bcrypt
    hashed = bcrypt.hashpw(pw, setting)

    return "v3" + base64.b64encode(hashed).decode("ascii").rstrip("=")


def generate_token_v3(
    device: str,
    version_code: int = DEFAULT_VERSION_CODE,
    package: str = DEFAULT_PACKAGE,
    ts: int | None = None,
    max_ahead: int = _MAX_AHEAD,
) -> tuple[str, int]:
    """生成 v3 token，自动处理 Invalid salt 问题。

    Args:
        device: X-App-Device 值
        version_code: App versionCode
        package: 包名
        ts: 指定时间戳。None 则用当前时间。
        max_ahead: 时间戳前探窗口大小（秒）

    Returns:
        (token, used_ts) 元组。used_ts 是实际使用的时间戳。

    Raises:
        RuntimeError: 在 +0..max_ahead 窗口内均无法生成有效盐
    """
    if ts is not None:
        token = _generate_token_at(device, ts, version_code, package)
        return token, ts

    start_ts = int(time.time())
    last_err: Exception | None = None
    for offset in range(max_ahead + 1):
        ts = start_ts + offset
        try:
            return _generate_token_at(device, ts, version_code, package), ts
        except ValueError as exc:
            if "Invalid salt" in str(exc):
                last_err = exc
                continue
            raise
    raise RuntimeError(
        f"在 +0..+{max_ahead}s 窗口内均无法生成有效 v3 盐: {last_err}"
    )


# 兼容旧接口：client.py 原来调用 generate_token(device_code)
def generate_token(device: str) -> str:
    """旧接口兼容 — 只返回 token 字符串，丢弃时间戳。

    注意：v3 token 与时间戳绑定，调用方应尽量用 generate_token_v3()
    以获取实际时间戳（用于请求头 X-App-Time 或调试）。
    """
    token, _ = generate_token_v3(device)
    return token