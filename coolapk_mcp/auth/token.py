"""Token V2 生成 — 对应 TokenCreator.GetTokenWithDeviceCode"""

import base64
import hashlib
import time

import bcrypt

# V2 salt key（对应 C# 源码中的常量）
_V2_SALT_KEY = "dcf01e569c1e3db93a3d0fcf191a622c"

# bcrypt 自定义 base64 字母表（不同于标准 base64）
_BCRYPT_BASE64 = "./ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
_BCRYPT_LOOKUP = {c: i for i, c in enumerate(_BCRYPT_BASE64)}


def _md5_hex(input_str: str) -> str:
    """UTF-8 编码后做 MD5，返回小写十六进制（去连字符）"""
    return hashlib.md5(input_str.encode("utf-8")).hexdigest()


def _base64_encode(input_str: str) -> str:
    """标准 Base64 编码，去除尾部 ="""
    return base64.b64encode(input_str.encode("utf-8")).decode().rstrip("=")


def _bcrypt_b64_decode(s: str, nbytes: int = 16) -> bytes:
    """用 bcrypt base64 字母表解码字符串为原始字节。
    与 BCrypt.Net 的 decode_base64 行为一致。
    """
    result = bytearray()
    i = 0
    remaining = nbytes
    while remaining > 0 and i + 1 < len(s):
        c1 = _BCRYPT_LOOKUP.get(s[i], 0)
        c2 = _BCRYPT_LOOKUP.get(s[i + 1], 0)
        i += 2

        result.append((c1 << 2) | ((c2 & 0x30) >> 4))
        remaining -= 1
        if remaining == 0 or i >= len(s):
            break

        c3 = _BCRYPT_LOOKUP.get(s[i], 0)
        i += 1
        result.append(((c2 & 0x0F) << 4) | ((c3 & 0x3C) >> 2))
        remaining -= 1
        if remaining == 0 or i >= len(s):
            break

        c4 = _BCRYPT_LOOKUP.get(s[i], 0)
        i += 1
        result.append(((c3 & 0x03) << 6) | c4)
        remaining -= 1

    return bytes(result[:nbytes])


def _bcrypt_b64_encode(data: bytes) -> str:
    """用 bcrypt base64 字母表编码原始字节。
    产生 Python bcrypt 库能接受的有效盐字符串。
    """
    result = []
    i = 0
    while i < len(data):
        b1 = data[i]
        b2 = data[i + 1] if i + 1 < len(data) else 0
        b3 = data[i + 2] if i + 2 < len(data) else 0

        result.append(_BCRYPT_BASE64[(b1 >> 2) & 0x3F])
        result.append(_BCRYPT_BASE64[((b1 & 0x03) << 4) | ((b2 >> 4) & 0x0F)])
        result.append(_BCRYPT_BASE64[((b2 & 0x0F) << 2) | ((b3 >> 6) & 0x03)])
        result.append(_BCRYPT_BASE64[b3 & 0x3F])
        i += 3

    # 16 字节 → ceil(16*4/3) = 22 字符，取前 22 个
    return "".join(result)[:22]


def generate_token(device_code: str) -> str:
    """
    Token V2 生成算法，精确对应 TokenCreator.GetTokenWithDeviceCode()。

    步骤与 C# 源码一一对应，bcrypt 盐的处理方式：
    C# BCrypt.Net 用自定义 base64 字母表解码盐字符串得到 16 字节。
    Python bcrypt 要求盐字符串是有效的 bcrypt base64 编码。
    解法：先按 bcrypt base64 解码 C# 格式的盐得到 16 字节，
    再用 bcrypt base64 重新编码，确保两边用完全相同的盐字节数据。
    """
    time_stamp = str(int(time.time()))
    base64_ts = _base64_encode(time_stamp)
    md5_ts = _md5_hex(time_stamp)
    md5_dev = _md5_hex(device_code)

    token_str = (
        f"token://com.coolapk.market/{_V2_SALT_KEY}"
        f"?{md5_ts}${md5_dev}&com.coolapk.market"
    )
    base64_token = _base64_encode(token_str)
    md5_base64_token = _md5_hex(base64_token)
    md5_token_str = _md5_hex(token_str)

    # 与 C# 一致：构造盐字符串，截取前 31 字符 + "u"
    salt_chars = f"{base64_ts}/{md5_token_str}"[:24] + "u"
    # 解码为 16 字节（与 BCrypt.Net 行为一致）
    salt_bytes = _bcrypt_b64_decode(salt_chars, 16)
    # 用 bcrypt base64 重新编码，得到 Python bcrypt 可接受的盐
    salt_b64 = _bcrypt_b64_encode(salt_bytes)
    bcrypt_salt = f"$2b$10${salt_b64}".encode("utf-8")

    bcrypt_hash = bcrypt.hashpw(
        md5_base64_token.encode("utf-8"),
        bcrypt_salt,
    ).decode("utf-8")

    # Python bcrypt 输出 $2b$ 前缀，但 C# BCrypt.Net 输出 $2y$ 前缀
    # token 包含 bcrypt hash 字符串，前缀不同会导致 API 验证失败
    bcrypt_hash = bcrypt_hash.replace("$2b$", "$2y$", 1)

    return "v2" + _base64_encode(bcrypt_hash)
