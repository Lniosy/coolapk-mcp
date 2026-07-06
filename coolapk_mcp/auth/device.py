"""设备码生成 — 对应 DeviceInfo.CreateDeviceCode()

注意：v3 token 写操作实测可用 qiuyurs 仓库的默认 device 码（2026-07-06 验证）。
该 device 码已在酷安 v16.2.0 上验证 like/follow/message 等写操作成功。
"""

# 已验证可用的默认 device 码（来源：qiuyurs/coolApkAPI 仓库）
# 实测：配合 v3 token + 真实 cookie，读+写操作均成功
DEFAULT_DEVICE_CODE = (
    "AZmV2N4UzN0UmZ3kDOzEzYgsjMwAjL2IjMwUjMuE0MRFEI7MkMxITM4AjMyAyOp1GZlJFI7kWbvFWaYByO"
    "gsDI7AyOzYGO3okVq1GWOlEez8WYLlkWKVWbllzX3pUTjFTcjx2aPVFR"
)


def generate_device_code() -> str:
    """返回已验证可用的默认 device 码。

    之前用随机生成的假设备码，读操作可用但写操作不可靠。
    2026-07-06 改用 qiuyurs 仓库验证过的 device 码，读+写均稳定。
    """
    return DEFAULT_DEVICE_CODE
