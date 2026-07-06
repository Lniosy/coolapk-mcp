"""libauth.so blob 提取与缓存 — v3 token 算法的基础数据

酷安 v3 X-App-Token 的 salt 第二段依赖一个从 libauth.so 解密出的 base64 blob。
该 blob 按 ((ts + version_code) % 100) * 4 + 0x80 索引切片，再 base64 解码得到 segment。

提取流程（一次性，结果缓存到磁盘）：
1. 从 coolapk APK 读取 lib/arm64-v8a/libauth.so
2. 在 .so 内匹配长度 >= 1000 的 base64 文本候选
3. 对每个候选 base64 解码后逐字节 XOR 0x5A
4. 选"可打印字符比例最高"的候选作为目标 blob
5. 缓存 phase2（XOR 后的 bytes）到 ~/.coolapk-mcp/auth_blob.bin

算法来源：https://github.com/qiuyurs/coolApkAPI （coolapk_token.py + docs/TOKEN_ALGORITHM.md）
验证：2026-07-06 在酷安 v16.2.0 / versionCode=2604201 上实测，读+写操作均成功。
"""

from __future__ import annotations

import base64
import re
import zipfile
from pathlib import Path

from coolapk_mcp.config import CONFIG_DIR

# 缓存文件路径
BLOB_CACHE_FILE = CONFIG_DIR / "auth_blob.bin"
APK_CACHE_FILE = CONFIG_DIR / "coolapk.apk"

# XOR 常量
_XOR_KEY = 0x5A

# blob 候选的最小长度（base64 文本字符数）
_MIN_BLOB_LEN = 1000


def _find_blob_bytes(libauth_bytes: bytes) -> bytes:
    """在 libauth.so 二进制里定位 token blob，返回 XOR 解密后的 phase2 bytes。

    libauth.so 内嵌一个长 base64 文本，base64 解码后逐字节 XOR 0x5A 得到 phase2。
    phase2 是一段 ASCII base64 文本，按索引切片再 base64 解码得到 segment。
    选择标准：XOR 后可打印字符比例最高的候选。
    """
    candidates = re.findall(rb"[A-Za-z0-9+/]{%d,}" % _MIN_BLOB_LEN, libauth_bytes)
    if not candidates:
        raise RuntimeError("libauth.so 内未找到 base64 blob 候选")

    best_phase2: bytes | None = None
    best_score = -1.0
    for cand in candidates:
        try:
            decoded = base64.b64decode(cand, validate=True)
        except Exception:
            continue
        if not decoded:
            continue
        xored = bytes(b ^ _XOR_KEY for b in decoded)
        printable = sum(1 for c in xored if 32 <= c < 127)
        score = printable / len(xored)
        if score > best_score:
            best_score = score
            best_phase2 = xored

    if best_phase2 is None:
        raise RuntimeError("libauth.so 内的 base64 候选均无法解码")

    return best_phase2


def extract_blob_from_apk(apk_path: str | Path) -> bytes:
    """从 APK 提取 phase2 blob。

    Args:
        apk_path: coolapk base.apk 路径

    Returns:
        phase2 bytes（XOR 解密后的 blob）
    """
    apk_path = Path(apk_path)
    with zipfile.ZipFile(apk_path, "r") as zf:
        # 优先 arm64-v8a，不存在则回退其他 arch
        names = zf.namelist()
        so_name = None
        for arch in ("arm64-v8a", "armeabi-v7a", "x86_64"):
            candidate = f"lib/{arch}/libauth.so"
            if candidate in names:
                so_name = candidate
                break
        if so_name is None:
            # 模糊匹配
            matches = [n for n in names if n.endswith("libauth.so")]
            if not matches:
                raise RuntimeError(f"APK 内未找到 libauth.so: {apk_path}")
            so_name = matches[0]
        libauth = zf.read(so_name)

    return _find_blob_bytes(libauth)


def load_blob(apk_path: str | Path | None = None) -> bytes:
    """加载 phase2 blob，优先读缓存。

    Args:
        apk_path: 可选的 APK 路径。若提供且缓存不存在，则从该 APK 提取并缓存。
                  若未提供且缓存不存在，尝试 ~/.coolapk-mcp/coolapk.apk。

    Returns:
        phase2 bytes
    """
    if BLOB_CACHE_FILE.exists():
        return BLOB_CACHE_FILE.read_bytes()

    # 缓存不存在，从 APK 提取
    if apk_path is None:
        apk_path = APK_CACHE_FILE
    apk_path = Path(apk_path)
    if not apk_path.exists():
        raise RuntimeError(
            f"未找到 libauth blob 缓存 ({BLOB_CACHE_FILE})，也未找到 APK ({apk_path})。"
            " 请通过 `coolapk login --adb` 或手动提取 libauth.so blob。"
        )

    blob = extract_blob_from_apk(apk_path)
    save_blob(blob)
    return blob


def save_blob(blob: bytes) -> None:
    """缓存 phase2 blob 到磁盘"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    BLOB_CACHE_FILE.write_bytes(blob)


def cache_apk(apk_path: str | Path) -> None:
    """复制 APK 到 config 目录作为 blob 来源备份"""
    apk_path = Path(apk_path)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    APK_CACHE_FILE.write_bytes(apk_path.read_bytes())


def get_blob() -> bytes:
    """获取已加载的 blob，若未缓存则报错。

    不同于 load_blob，这个方法不会尝试提取，只读缓存。
    用于 token_v3 生成时的快速路径。
    """
    if not BLOB_CACHE_FILE.exists():
        raise RuntimeError(
            "libauth blob 未缓存。请先运行 `coolapk login --adb` 从手机提取，"
            "或手动指定 APK 路径运行 `coolapk auth --extract <apk_path>`。"
        )
    return BLOB_CACHE_FILE.read_bytes()