# Changelog

## [Unreleased]

### Fixed
- X-App-Token 在未提取 libauth blob 时自动回退 v2 算法：v3 依赖从手机提取的 blob，未运行 `coolapk login --adb` / `auth --extract` 的环境下 v3 会抛 RuntimeError，此前直接导致请求失败；现改为 v3 优先、失败后记忆性回退 v2（只降级一次，不回切）

### Added
- `comments` 命令：热门评论（hotReplyList）+ 经作者动态列表恢复正文，作为 `feed/detail` 被风控时的替代链路（#5）
- `app` 命令：按包名查应用详情（版本/体积/开发者/评论数）

## [0.2.0] - 2026-10-22

### Docs
- README 首屏改为专业图文 Hero + badges + 场景表
- 新增 Cursor / Claude `mcp.json` 配置说明
- 新增「生态适配」：Qx / qxcoolapk 友链与 Workbench 使用案例配图（#4）
- 新增「已知限制」：说明 `feed/detail` captcha（#5）
- 弱化实现细节中的敏感措辞

### Meta
- Topics 已更新：ai, claude, coolapk, cursor, mcp, mcp-server, python
