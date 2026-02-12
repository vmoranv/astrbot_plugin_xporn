# AstrBot X-Porn 插件

Twitter 视频排行查询插件，支持获取排行榜、搜索、热门视频等功能。

## 功能

- 📺 **排行榜** - 获取 Twitter 视频排行榜
- 🔍 **搜索** - 根据关键词搜索视频
- 🔥 **热门** - 获取热门推荐视频
- 🎲 **随机** - 随机推荐一个视频
- 📄 **详情** - 获取指定视频的详细信息

## 命令使用

所有命令前缀为 `xporn` 或简写 `xp`：

```
xporn help         # 显示帮助信息
xporn rank [页码]  # 获取排行榜（默认第1页）
xporn search <关键词>  # 搜索视频
xporn hot          # 获取热门视频
xporn random       # 随机推荐
xporn info <视频ID>  # 获取视频详情
```

## 示例

```
xporn rank          # 获取排行榜第1页
xporn rank 2        # 获取排行榜第2页
xporn search anime  # 搜索动漫相关视频
xporn hot           # 获取热门视频
xporn random        # 随机推荐
xporn info abc123   # 获取视频详情
```

## 安装

1. 将插件目录放到 AstrBot 的 `data/plugins/` 目录下
2. 重启 AstrBot 或在 WebUI 中重载插件
3. 安装依赖：`pip install aiohttp`

## 配置

在 WebUI 中配置以下选项：

| 选项 | 说明 | 默认值 |
|------|------|--------|
| 打码程度 | 封面打码程度 (0=无, 1=轻微, 2=中度, 3=重度) | 0 |
| 代理地址 | 代理服务器地址（如 http://127.0.0.1:7890） | 空 |
| 代理认证 | 代理认证（用户名/密码） | 空 |
| 请求超时 | 请求超时时间（秒） | 15 |
| 每页显示 | 每页最大显示数量 | 10 |

## 依赖

- Python 3.8+
- aiohttp

## 仓库

https://github.com/vmoranv/astrbot_plugin_xporn

## 许可证

MIT
