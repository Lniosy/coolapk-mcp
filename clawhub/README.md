# Coolapk Skill for Claude Code

AI 原生的酷安社区搜索工具，让 Claude Code 直接通过 CLI 搜索酷安社区内容。

## 功能

- **搜索**: 帖子、用户、话题、应用
- **浏览**: 首页推荐/热门/最新、帖子详情+回复
- **用户**: 用户资料、用户动态列表
- **话题**: 话题详情、话题下帖子
- **交互**: 点赞、回复、关注（需登录）
- **通知**: 未读计数、各类通知详情

## 安装

```bash
clawhub install coolapk
```

安装后 Claude Code 会自动加载此 skill，可直接使用 `coolapk` CLI 命令。

## 底层依赖

本 skill 依赖 [coolapk-mcp](https://github.com/lniosy/coolapk-mcp) Python 包，首次使用时自动通过 pip 安装。

## 输出格式

所有命令输出精简 JSON，自动排除空值字段，最大限度节省 token。

## 许可

MIT
