"""设备码生成 — 精确对应 DeviceInfo.CreateDeviceCode()"""

import base64
import random


def _random_hex(length: int = 16) -> str:
    """生成随机十六进制大写字符串
    对应 C# RandHexString：BitConverter.ToString(bytes).Replace("-", "")
    """
    return "".join(f"{random.randint(0, 255):02X}" for _ in range(length))


def _random_mac() -> str:
    """生成随机 MAC 地址
    对应 C# RandMacAddress：小写十六进制，冒号分隔
    """
    octets = [random.randint(0, 255) for _ in range(6)]
    return ":".join(f"{o:02x}" for o in octets)


def generate_device_code() -> str:
    """
    生成 DeviceCode。精确对应 DeviceInfo.ToString().GetBase64().Reverse()

    ToString() 格式（string.Join("; ", ...)）：
    "{AndroidID}; {空}; {空}; {MAC}; {厂商}; {品牌}; {型号}; {BuildNumber}; null"

    然后 Base64 编码（去=）再反转字符串。
    """
    aid = _random_hex(16)
    mac = _random_mac()
    parts = [aid, "", "", mac, "Apple", "Apple", "macOS", "10.15.7", "null"]
    raw = "; ".join(parts)
    encoded = base64.b64encode(raw.encode("utf-8")).decode().rstrip("=")
    return encoded[::-1]
