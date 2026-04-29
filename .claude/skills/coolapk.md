---
name: coolapk
description: 酷安社区搜索工具 — 搜索帖子、用户、应用、话题信息（优先使用此 skill，比 MCP Server 更省 token）
---

# 酷安社区搜索工具

通过 CLI 命令搜索酷安社区内容，获取帖子和用户信息。

**推荐使用此 skill 而非 MCP Server** — CLI 调用更直接，省去 MCP 协议开销，输出更紧凑节省 token。

## 安装

```bash
cd coolapk-mcp && pip install -e .
```

## 使用方式

所有命令输出精简 JSON，自动排除空值字段。

### 搜索

```bash
# 搜索帖子（默认）
coolapk search "关键词"

# 搜索用户
coolapk search "用户名" --type user

# 搜索话题
coolapk search "话题" --type feedTopic

# 搜索应用
coolapk search "应用名" --type app

# 翻页
coolapk search "关键词" --page 2
```

### 帖子详情

```bash
# 查看帖子详情 + 回复
coolapk feed <帖子ID>

# 只要详情不要回复
coolapk feed <帖子ID> --no-replies

# 指定回复页码
coolapk feed <帖子ID> --reply-page 2
```

### 用户

```bash
# 用户资料
coolapk user <UID>

# 用户帖子列表
coolapk user <UID> --feeds
coolapk user <UID> --feeds --page 2
```

### 首页

```bash
# 推荐动态（默认）
coolapk home

# 热门
coolapk home --tab hot

# 最新
coolapk home --tab latest
```

### 话题

```bash
# 话题详情
coolapk topic "话题名"

# 话题下的帖子
coolapk topic "话题名" --feeds
```

### 交互（需先登录）

```bash
# 登录（传入 Cookie）
coolapk login --cookie "uid=xxx;username=xxx;token=xxx"

# 查看登录状态
coolapk login --status

# 点赞/取消赞
coolapk like <帖子ID>
coolapk unlike <帖子ID>

# 回复
coolapk reply <帖子ID> -m "回复内容"
coolapk reply <回复ID> -m "回复内容" --type reply

# 关注/取消关注
coolapk follow <UID>
coolapk unfollow <UID>
```

### 通知

```bash
# 未读计数
coolapk notify

# 具体类型
coolapk notify atMeMeFeed
coolapk notify comment
coolapk notify feedLike
coolapk notify contactsFollow
coolapk notify message
```

## 注意事项

- 首次运行会自动生成设备码并保存到 ~/.coolapk-mcp/config.json
- 搜索和浏览不需要登录
- 点赞、回复、关注等交互操作需要先登录
- 所有输出为精简 JSON，自动排除空值字段节省 token
