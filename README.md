<p align="center">
  <img src="docs/assets/hero.jpg" alt="coolapk-mcp — 酷安社区 MCP Server + CLI" width="100%"/>
</p>

<p align="center">
  <strong>酷安社区 · AI 原生搜索工具</strong><br/>
  在 Cursor / Claude 里直接搜酷安：动态、热榜、应用、二手、话题一键拉进上下文。
</p>

<p align="center">
  <a href="https://github.com/Lniosy/coolapk-mcp/stargazers"><img src="https://img.shields.io/github/stars/Lniosy/coolapk-mcp?style=flat-square&logo=github" alt="Stars"/></a>
  <a href="https://github.com/Lniosy/coolapk-mcp/network/members"><img src="https://img.shields.io/github/forks/Lniosy/coolapk-mcp?style=flat-square" alt="Forks"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="MIT"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-%3E%3D3.10-blue?style=flat-square&logo=python&logoColor=white" alt="Python"/></a>
  <a href="#mcp-server"><img src="https://img.shields.io/badge/MCP-Server-0ea5e9?style=flat-square" alt="MCP"/></a>
  <a href="#cursor--claude-配置"><img src="https://img.shields.io/badge/Cursor-Ready-black?style=flat-square" alt="Cursor"/></a>
</p>

<p align="center">
  <a href="#快速开始">快速开始</a> ·
  <a href="#功能">功能</a> ·
  <a href="#cursor--claude-配置">Cursor / Claude</a> ·
  <a href="#生态适配">生态适配</a> ·
  <a href="#已知限制">已知限制</a> ·
  <a href="#license">License</a>
</p>

---

## 这是什么

`coolapk-mcp` 把酷安社区做成 **MCP Server + CLI**，让 AI 编程助手能：

| 场景 | 能做什么 |
|------|----------|
| 📸 摄影图文 | 搜美女摄影、风光、样张帖 |
| 🐑 羊毛福利 | 扫活动、抽奖、试用信息 |
| 🔬 前沿科技 | 盯数码/开发热帖，少刷到吐 |
| 📱 淘二手机 | 二手区盯性价比机型 |
| 🧩 应用发现 | 搜应用、话题、用户 |

> 开源自用维护中 · MIT · 当前 **27★ / 5 fork**

## 快速开始

```bash
# 需要 Python >= 3.10
git clone https://github.com/Lniosy/coolapk-mcp.git
cd coolapk-mcp
pip install -e .
```

装好后两条路任选：

1. **MCP Server**（推荐接 Cursor / Claude Desktop）
2. **CLI**（脚本、Agent Skill、管道调用更省 token）

## 功能

- **搜索** — 帖子、用户、话题、应用
- **帖子详情** — 完整内容 + 评论（见 [已知限制](#已知限制)）
- **用户资料** — 个人信息、发帖列表
- **首页动态** — 推荐 / 热门 / 最新
- **话题浏览** — 话题详情 + 话题下帖子
- **交互操作** — 点赞、回复、关注（需登录）
- **精简输出** — 自动排除空值字段，省 AI 上下文 token
- **图片 URL** — 搜索/详情直接返回 `images` 列表（[#1](https://github.com/Lniosy/coolapk-mcp/issues/1) 已修）

## Cursor / Claude 配置

### Cursor（`~/.cursor/mcp.json` 或项目 `.cursor/mcp.json`）

```json
{
  "mcpServers": {
    "coolapk": {
      "command": "coolapk-mcp"
    }
  }
}
```

若用本地源码路径：

```json
{
  "mcpServers": {
    "coolapk": {
      "command": "python",
      "args": ["-m", "coolapk_mcp.server"],
      "cwd": "/绝对路径/coolapk-mcp"
    }
  }
}
```

### Claude Code / Desktop

```json
{
  "mcpServers": {
    "coolapk": {
      "command": "coolapk-mcp"
    }
  }
}
```

### Claude Code Skill（更省 token）

项目内置 `.claude/skills/coolapk.md`，clone 进工作目录后 Claude Code 可直接当 skill 用；CLI 无协议开销，输出更紧凑。

### 注册的 MCP Tools

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
coolapk search "关键词"
coolapk search "用户名" --type user
coolapk feed <帖子ID>
coolapk feed <帖子ID> --no-replies
coolapk user <UID>
coolapk user <UID> --feeds
coolapk home --tab hot
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

## 生态适配

社区已有基于本项目的桌面端适配，欢迎继续扩展：

### [qxcoolapk](https://github.com/mcxen/qx-plugins) — Qx 快捷启动器插件

[@mcxen](https://github.com/mcxen) 将 Coolapk MCP 接口适配为 [Qx](https://github.com/mcxen/qx)（Mac / Windows 快捷启动器）沙盒插件 **qxcoolapk**，可在 Qx Workbench 里浏览热榜、数码动态、完整帖文、图片与回复。

授权与署名均 OK，欢迎继续使用与改进。原始讨论见 [#4](https://github.com/Lniosy/coolapk-mcp/issues/4)。

<p align="center">
  <img src="docs/assets/qxcoolapk-workbench.jpg" alt="qxcoolapk 在 Qx Workbench 中浏览酷安动态" width="100%"/>
  <br/>
  <em>使用案例：Qx Workbench 三栏浏览酷安热帖 / 数码 / 完整正文</em>
</p>

### 友链

| 项目 | 说明 |
|------|------|
| [Qx](https://github.com/mcxen/qx) | Mac / Windows 快捷启动器（Quick And Quiet Starter） |
| [qx-plugins](https://github.com/mcxen/qx-plugins) | Qx 插件市场索引（含 qxcoolapk） |
| [Coolapk-Lite](https://github.com/Coolapk-UWP/Coolapk-Lite) | 酷安第三方客户端参考实现（致谢） |

想把 coolapk-mcp 接到你的产品？开个 Issue 或 PR，README 生态区欢迎挂友链。

## 已知限制

- **`/v6/feed/detail` 验证码**：新版酷安对详情接口风控更严，部分环境会稳定返回 `err_request_captcha_v2`；搜索、列表、用户动态、评论等读接口通常仍可用。详见 [#5](https://github.com/Lniosy/coolapk-mcp/issues/5)。临时思路：从作者动态列表按 ID 回落读公开帖（不保证字段完整）。
- 请合理使用接口频率，遵守酷安用户协议与当地法规；本项目仅作个人/研究向信息检索，不提供绕过风控或破解软件相关能力。

## 技术实现（简述）

- Token 生成与设备标识模拟，兼容公开 API 访问模式
- Pydantic 精简序列化（`exclude_defaults=True`），输出体积约为原始响应的约 10%

## 项目结构

```
coolapk_mcp/
├── server.py          # MCP Server 入口
├── cli.py             # CLI 入口
├── client.py          # HTTP 客户端 + API 封装
├── models.py          # Pydantic 数据模型
├── config.py          # 配置管理
└── auth/
    ├── token.py       # Token 生成
    └── device.py      # 设备码生成
```

## 致谢

- API 参考了 [Coolapk-UWP/Coolapk-Lite](https://github.com/Coolapk-UWP/Coolapk-Lite)
- 生态适配：[mcxen/qx](https://github.com/mcxen/qx) · [mcxen/qx-plugins](https://github.com/mcxen/qx-plugins)（qxcoolapk）

## License

[MIT](LICENSE)
