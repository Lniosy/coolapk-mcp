# coolapk-mcp

酷安社区 MCP Server + CLI — AI 原生搜索工具

让 AI 工具（Claude Code、Cursor 等）直接调用酷安的搜索和浏览能力，作为社区信息源使用。

## 功能

- **搜索** — 帖子、用户、话题、应用
- **帖子详情** — 完整内容 + 评论区
- **用户资料** — 个人信息、发帖列表
- **首页动态** — 推荐 / 热门 / 最新
- **话题浏览** — 话题详情 + 话题下帖子
- **交互操作** — 点赞、回复、关注（需登录）
- **精简输出** — 自动排除空值字段，节省 AI 上下文 token

## 安装

```bash
pip install -e .
```

需要 Python >= 3.10。

## MCP Server

在 Claude Code 的 MCP 配置中添加：

```json
{
  "mcpServers": {
    "coolapk": {
      "command": "coolapk-mcp"
    }
  }
}
```

注册的 Tools：

| Tool | 说明 |
|------|------|
| `coolapk_search` | 搜索帖子/用户/应用/话题 |
| `coolapk_feed_detail` | 帖子详情 + 回复 |
| `coolapk_user_profile` | 用户资料 |
| `coolapk_user_feeds` | 用户发帖列表 |
| `coolapk_home` | 首页动态 |
| `coolapk_topic` | 话题详情/帖子 |

## CLI 使用

所有命令输出紧凑 JSON，适合 AI 解析。

```bash
# 搜索
coolapk search "关键词"
coolapk search "用户名" --type user

# 帖子详情（含回复）
coolapk feed <帖子ID>
coolapk feed <帖子ID> --no-replies

# 用户
coolapk user <UID>
coolapk user <UID> --feeds

# 首页
coolapk home --tab hot

# 话题
coolapk topic "小米解锁BL"
coolapk topic "小米解锁BL" --feeds
```

### 交互操作（需登录）

```bash
coolapk login --cookie "uid=xxx;username=xxx;token=xxx"
coolapk like <帖子ID>
coolapk reply <帖子ID> -m "回复内容"
coolapk follow <UID>
```

## 技术实现

- **Token V2 认证** — 逆向酷安 Token 生成算法（MD5 + Base64 + bcrypt），解决了 Python bcrypt 与 C# BCrypt.Net 的盐编码兼容问题
- **设备码模拟** — 生成合法的设备标识通过 API 验证
- **精简序列化** — Pydantic 模型 + `exclude_defaults=True`，输出体积比原始 API 响应减少约 90%

## 项目结构

```
coolapk_mcp/
├── server.py          # MCP Server 入口
├── cli.py             # CLI 入口
├── client.py          # HTTP 客户端 + API 封装
├── models.py          # Pydantic 数据模型
├── config.py          # 配置管理
└── auth/
    ├── token.py       # Token V2 生成
    └── device.py      # 设备码生成
```

## 致谢

API 逆向参考了 [Coolapk-UWP/Coolapk-Lite](https://github.com/Coolapk-UWP/Coolapk-Lite) 项目。

## License

MIT
