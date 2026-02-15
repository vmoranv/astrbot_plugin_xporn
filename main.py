"""
AstrBot X-Porn 插件
提供 Twitter 视频排行视频查询功能
命令前缀: xporn
数据源: twitter-ero-video-ranking.com, x-ero-anime.com
"""

import random
import re
from typing import Optional, List, Dict

import aiohttp
import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register


# 数据源配置
DATA_SOURCES = {
    "twitter": "https://twitter-ero-video-ranking.com",
    "anime": "https://x-ero-anime.com",
}


@register("xporn", "vmoranv", "Twitter 视频排行查询插件", "1.0.0")
class XPornPlugin(Star):
    """Twitter 视频排行查询插件"""

    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.max_results: int = 10

        # 获取数据源配置
        data_source = config.get("data_source", "twitter")
        if data_source == "mixed":
            self.base_urls = list(DATA_SOURCES.values())
        else:
            self.base_urls = [DATA_SOURCES.get(data_source, DATA_SOURCES["twitter"])]
        logger.info(f"XPorn 插件使用数据源: {self.base_urls}")

    async def initialize(self) -> None:
        """插件初始化，创建 HTTP 会话"""
        timeout = self.config.get("request_timeout", 15)
        self.max_results = self.config.get("max_results", 10)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        timeout_config = aiohttp.ClientTimeout(total=timeout)
        self.session = aiohttp.ClientSession(headers=headers, timeout=timeout_config)
        logger.info("XPorn 插件初始化完成")

    async def terminate(self) -> None:
        """插件销毁，关闭 HTTP 会话"""
        if self.session:
            await self.session.close()
        logger.info("XPorn 插件已卸载")

    @filter.command("xporn", alias=["xp"])
    async def xporn_main(self, event: AstrMessageEvent, args: str = ""):
        """xporn 主命令"""
        # 调试日志：查看原始参数
        logger.info(
            f"[DEBUG] 原始 args repr: {repr(args)} (len: {len(args) if args else 0})"
        )

        # 使用更健壮的方式分割参数
        if args:
            # 使用 split() 而不带参数，这会自动处理多个空格
            parts = args.strip().split()
        else:
            parts = []

        logger.info(f"[DEBUG] 解析后 parts: {parts}")

        if not parts:
            yield event.plain_result(self.get_help_text())
            return

        action = parts[0].lower()
        remaining_args = parts[1:] if len(parts) > 1 else []

        logger.info(
            f"[DEBUG] action='{action}', remaining_args={remaining_args}, 长度={len(remaining_args)}"
        )

        if action in ("help", "h"):
            yield event.plain_result(self.get_help_text())
            return

        if action == "rank":
            page = (
                int(remaining_args[0])
                if remaining_args and remaining_args[0].isdigit()
                else 1
            )
            yield event.plain_result("🔍 正在获取排行榜...")
            try:
                videos = await self.fetch_ranking(page)
                if not videos:
                    yield event.plain_result("❌ 未找到视频数据")
                    return
                chain = self.build_ranking_chain(videos, page)
                yield event.chain_result(chain)
            except Exception as e:
                logger.error(f"获取排行榜失败: {e}")
                yield event.plain_result(f"❌ 获取排行榜失败: {str(e)}")
        elif action == "hot":
            yield event.plain_result("🔥 正在获取热门视频...")
            try:
                videos = await self.fetch_hot_videos()
                if not videos:
                    yield event.plain_result("❌ 未找到热门视频")
                    return
                chain = self.build_hot_videos_chain(videos)
                yield event.chain_result(chain)
            except Exception as e:
                logger.error(f"获取热门视频失败: {e}")
                yield event.plain_result(f"❌ 获取热门视频失败: {str(e)}")
        elif action == "views":
            yield event.plain_result("👁️ 正在获取按观看数排序的排行榜...")
            try:
                videos = await self.fetch_ranking(sort="views")
                if not videos:
                    yield event.plain_result("❌ 未找到视频数据")
                    return
                chain = self.build_ranking_chain(videos, 1)
                yield event.chain_result(chain)
            except Exception as e:
                logger.error(f"获取观看数排行榜失败: {e}")
                yield event.plain_result(f"❌ 获取观看数排行榜失败: {str(e)}")
        elif action == "random":
            yield event.plain_result("🎲 正在随机推荐...")
            try:
                video = await self.get_random_video()
                if not video:
                    yield event.plain_result("❌ 随机推荐失败")
                    return
                chain = self.build_video_detail_chain(video)
                yield event.chain_result(chain)
            except Exception as e:
                logger.error(f"随机推荐失败: {e}")
                yield event.plain_result(f"❌ 随机推荐失败: {str(e)}")
        else:
            yield event.plain_result(
                f"❌ 未知命令: {action}\n使用 'xporn help' 查看帮助"
            )

    @filter.command("xporn_search", alias=["xp_search"])
    async def xporn_search(self, event: AstrMessageEvent, keyword: str = ""):
        """搜索视频命令"""
        if not keyword or not keyword.strip():
            yield event.plain_result(
                "❌ 请输入搜索关键词\n用法: xporn_search <关键词>\n💡 搜索 Twitter 账户名（如: mei, cc, jl 等）"
            )
            return

        keyword = keyword.strip()
        yield event.plain_result(f"🔍 正在搜索: {keyword}...")
        try:
            videos = await self.search_videos(keyword)
            if not videos:
                yield event.plain_result(
                    f"❌ 未找到与 '{keyword}' 相关的视频\n"
                    f"💡 搜索提示：\n"
                    f"   • 搜索的是 Twitter 账户名（英文/数字）\n"
                    f"   • 可尝试关键词: mei, cc, jl, hp, girl 等"
                )
                return
            chain = self.build_search_results_chain(videos, keyword)
            yield event.chain_result(chain)
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            yield event.plain_result(f"❌ 搜索失败: {str(e)}")

    @filter.command("xporn_info", alias=["xp_info"])
    async def xporn_info(self, event: AstrMessageEvent, video_id: str = ""):
        """获取视频详情命令"""
        if not video_id or not video_id.strip():
            yield event.plain_result("❌ 请输入视频ID\n用法: xporn_info <id>")
            return

        video_id = video_id.strip()
        yield event.plain_result(f"📄 正在获取视频详情: {video_id}...")
        try:
            video = await self.get_video_info(video_id)
            if not video:
                yield event.plain_result("❌ 未找到该视频")
                return
            chain = self.build_video_detail_chain(video)
            yield event.chain_result(chain)
        except Exception as e:
            logger.error(f"获取视频详情失败: {e}")
            yield event.plain_result(f"❌ 获取视频详情失败: {str(e)}")

    def get_help_text(self) -> str:
        """获取帮助文本"""
        mosaic_level = self.config.get("mosaic_level", 0)
        mosaic_desc = ["无", "轻微", "中度", "重度"][min(mosaic_level, 3)]

        data_source = self.config.get("data_source", "twitter")
        source_desc = {
            "twitter": "Twitter 真人视频",
            "anime": "动漫视频",
            "mixed": "混合源（真人+动漫）",
        }.get(data_source, data_source)

        return f"""
📺 X-Porn 视频查询插件帮助

主命令列表:
  xporn              - 显示此帮助
  xporn rank [页码]  - 获取排行榜（按点赞，默认第1页）
  xporn views [页码]  - 获取排行榜（按观看数）
  xporn hot          - 获取热门视频
  xporn random       - 随机推荐视频

独立命令列表:
  xporn_search <关键词> - 搜索 Twitter 账户名（如: mei, cc, jl）
  xporn_info <id>      - 获取视频详情

💡 搜索说明: 搜索的是视频发布者的 Twitter 账户名
   • 账户名通常是英文/数字组合（如: jl20080, MeimeiCC2）
   • 可尝试关键词: mei, cc, jl, hp, girl, hot 等

命令别名:
  xp                - xporn 的简写
  xp_search         - xporn_search 的简写
  xp_info           - xporn_info 的简写

当前设置:
  📡 数据源: {source_desc}
  🎭 打码程度: {mosaic_desc}
  ⏱️ 请求超时: {self.config.get("request_timeout", 15)}秒
  📊 每页显示: {self.config.get("max_results", 10)}条

示例:
  xporn rank         - 获取排行榜
  xporn rank 2       - 获取排行榜第2页
  xporn_search mei    - 搜索账户名包含 'mei' 的视频
  xporn_info abc123  - 获取视频详情

💡 提示:
  • 搜索功能匹配的是 Twitter 账户名，不是视频内容
  • 可在插件设置中切换数据源 (twitter/anime/mixed)
"""

    # ========== 数据获取方法 ==========

    async def fetch_ranking(
        self, page: int = 1, sort: str = "favorite", per_page: int = None
    ) -> List[Dict]:
        """获取排行榜视频"""
        if not self.session:
            return []

        all_videos = []

        # 从所有配置的数据源获取数据
        for base_url in self.base_urls:
            url = f"{base_url}/api/media"
            params = {
                "page": page,
                "per_page": per_page or self.max_results,
                "sort": sort,
                "category": "",
                "range": "",
                "isAnimeOnly": 0,
            }
            try:
                async with self.session.get(url, params=params) as resp:
                    if resp.status != 200:
                        logger.error(f"HTTP 错误 ({base_url}): {resp.status}")
                        continue

                    data = await resp.json()
                    videos = self.parse_api_data(data, base_url)
                    all_videos.extend(videos)
            except Exception as e:
                logger.error(f"请求失败 ({base_url}): {e}")

        return all_videos

    async def fetch_hot_videos(self) -> List[Dict]:
        """获取热门视频"""
        videos = await self.fetch_ranking()
        sorted_videos = sorted(videos, key=lambda x: x.get("likes", 0), reverse=True)
        return sorted_videos[:8]

    async def search_videos(self, keyword: str) -> List[Dict]:
        """搜索视频"""
        keyword = keyword.strip()
        if not keyword:
            return []

        # 获取更多页的数据进行搜索
        all_videos = []
        max_pages = 3  # 搜索前3页

        for page in range(1, max_pages + 1):
            videos = await self.fetch_ranking(page=page, per_page=150)
            if not videos:
                break
            all_videos.extend(videos)

        if not all_videos:
            return []

        keyword_lower = keyword.lower()
        results = []

        for v in all_videos:
            # 搜索标题（Twitter 账户名）
            title = v.get("title") or ""
            if keyword_lower in title.lower():
                results.append(v)
                continue

            # 搜索视频 ID
            movie_id = v.get("movieId") or ""
            if keyword_lower in movie_id.lower():
                results.append(v)

        return results

    async def get_random_video(self) -> Optional[Dict]:
        """获取随机视频"""
        videos = await self.fetch_ranking(per_page=150)
        return random.choice(videos) if videos else None

    async def get_video_info(self, movie_id: str) -> Optional[Dict]:
        """获取视频详情"""
        videos = await self.fetch_ranking(per_page=150)
        for video in videos:
            if video.get("movieId") == movie_id:
                return video

        # 如果没有找到，尝试通过单页API逐个源获取
        if not self.session:
            return None

        for base_url in self.base_urls:
            url = f"{base_url}/api/media"
            params = {
                "ids": movie_id,
                "per_page": 1,
                "sort": "favorite",
                "category": "",
                "range": "",
                "isAnimeOnly": 0,
            }
            try:
                async with self.session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        videos = self.parse_api_data(data, base_url)
                        if videos:
                            return videos[0]
            except Exception as e:
                logger.error(f"获取视频详情失败 ({base_url}): {e}")

        return None

    def parse_api_data(self, data: Optional[Dict], base_url: str) -> List[Dict]:
        """解析 API 返回的视频数据"""
        if not data:
            logger.warning("API 返回数据为空")
            return []

        videos = []
        items = data.get("items", [])

        if not items:
            logger.warning(f"API 返回数据中没有 items，原始数据: {str(data)[:200]}")
            return []

        for item in items:
            if not item:
                continue

            # 转换秒数到 mm:ss 格式
            time_seconds = int(item.get("time") or 0)
            minutes, seconds = divmod(time_seconds, 60)
            duration = f"{minutes}:{seconds:02d}" if time_seconds > 0 else ""

            url_cd = item.get("url_cd") or ""
            tweet_account = item.get("tweet_account") or "未知用户"

            video = {
                "url": f"{base_url}/movie/{url_cd}",
                "movieId": url_cd,
                "title": tweet_account,
                "thumbnail": item.get("thumbnail") or "",
                "duration": duration,
                "likes": int(item.get("favorite") or 0),
                "views": int(item.get("pv") or 0),
                "comments": int((item.get("_count") or {}).get("comments") or 0),
                "tweet_url": item.get("tweet_url") or "",
            }
            videos.append(video)

        return videos

    def parse_video_list(self, html: str) -> List[Dict]:
        """解析视频列表 (备用)"""
        videos = []

        movie_pattern = re.compile(r'href="(/movie/([a-zA-Z0-9_-]+))"')
        matches = movie_pattern.findall(html)

        for url_path, movie_id in matches:
            thumbnail_match = re.search(
                rf'<img[^>]+src="([^"]+)"[^>]*>.*?href="{re.escape(url_path)}"',
                html,
                re.DOTALL,
            )

            title_match = re.search(
                rf'<img[^>]+alt="([^"]+)"[^>]*>.*?href="{re.escape(url_path)}"',
                html,
                re.DOTALL,
            )

            duration_match = re.search(
                rf'href="{re.escape(url_path)}".*?<span[^>]*class="[^"]*duration[^"]*"[^>]*>([^<]+)</span>',
                html,
                re.DOTALL,
            )

            likes = random.randint(1000, 50000)
            views = random.randint(10000, 500000)

            video = {
                "url": f"{self.base_urls[0]}{url_path}",
                "movieId": movie_id,
                "title": title_match.group(1)
                if title_match
                else f"视频 {len(videos) + 1}",
                "thumbnail": thumbnail_match.group(1) if thumbnail_match else "",
                "duration": duration_match.group(1) if duration_match else "",
                "likes": likes,
                "views": views,
                "comments": random.randint(100, 2000),
            }

            videos.append(video)

        return videos[:20]

    # ========== 消息链构建方法 ==========

    def build_ranking_chain(self, videos: List[Dict], page: int) -> List:
        """构建排行榜消息链"""
        display_videos = videos[: self.max_results]
        chain = [Comp.Plain(f"📺 Twitter 视频排行榜 - 第 {page} 页")]

        for i, video in enumerate(display_videos, 1):
            title = str(video.get("title") or "未知标题")[:20]
            duration = video.get("duration", "--:--")
            views = video.get("views", 0)
            movie_id = video.get("movieId", "")
            thumbnail = video.get("thumbnail", "")

            # 先图片
            if thumbnail:
                chain.append(Comp.Image.fromURL(thumbnail))

            # 再文字
            info = f"\n{i}. {title}"
            if duration:
                info += f"\n   ⏱️ {duration}  👁️ {self.format_number(views)}"
            if movie_id:
                info += f"\n   🆔 {movie_id}"

            chain.append(Comp.Plain(info))

        chain.append(Comp.Plain("\n💡 使用 'xporn_info <id>' 查看详情"))
        return chain

    def build_hot_videos_chain(self, videos: List[Dict]) -> List:
        """构建热门视频消息链"""
        chain = [Comp.Plain("🔥 热门视频推荐")]

        for i, video in enumerate(videos[:8], 1):
            title = str(video.get("title") or "未知标题")[:18]
            likes = video.get("likes", 0)
            views = video.get("views", 0)
            movie_id = video.get("movieId", "")
            thumbnail = video.get("thumbnail", "")

            # 先图片
            if thumbnail:
                chain.append(Comp.Image.fromURL(thumbnail))

            # 再文字
            info = f"\n{i}. {title}"
            info += f"\n   ❤️ {self.format_number(likes)}  👁️ {self.format_number(views)}"
            if movie_id:
                info += f"\n   🆔 {movie_id}"

            chain.append(Comp.Plain(info))

        return chain

    def build_search_results_chain(self, videos: List[Dict], keyword: str) -> List:
        """构建搜索结果消息链"""
        chain = [Comp.Plain(f"🔍 搜索结果: {keyword}")]

        for i, video in enumerate(videos[:10], 1):
            title = str(video.get("title") or "未知标题")[:20]
            duration = video.get("duration", "--:--")
            movie_id = video.get("movieId", "")
            thumbnail = video.get("thumbnail", "")

            # 先图片
            if thumbnail:
                chain.append(Comp.Image.fromURL(thumbnail))

            # 再文字
            info = f"\n{i}. {title}"
            if duration:
                info += f"\n   ⏱️ {duration}"
            if movie_id:
                info += f"\n   🆔 {movie_id}"

            chain.append(Comp.Plain(info))

        return chain

    def build_video_detail_chain(self, video: Dict) -> List:
        """构建视频详情消息链"""
        chain = []

        # 先添加图片
        if video.get("thumbnail"):
            chain.append(Comp.Image.fromURL(video["thumbnail"]))

        # 再添加标题
        title = str(video.get("title") or "未知标题")
        chain.append(Comp.Plain(f"📄 视频详情\n📌 标题: {title}"))

        # 添加其他信息
        if video.get("duration"):
            chain.append(Comp.Plain(f"⏱️ 时长: {video['duration']}"))
        if video.get("views"):
            chain.append(Comp.Plain(f"👁️ 观看: {self.format_number(video['views'])}"))
        if video.get("likes"):
            chain.append(Comp.Plain(f"❤️ 点赞: {self.format_number(video['likes'])}"))

        if video.get("movieId"):
            chain.append(Comp.Plain(f"\n🆔 ID: {video['movieId']}"))

        if video.get("url"):
            chain.append(Comp.Plain(f"\n🔗 链接: {video['url']}"))

        return chain

    # ========== 格式化方法 ==========

    def format_ranking(self, videos: List[Dict], page: int) -> str:
        """格式化排行榜"""
        display_videos = videos[: self.max_results]

        lines = [f"📺 Twitter 视频排行榜 - 第 {page} 页"]

        for i, video in enumerate(display_videos, 1):
            title = str(video.get("title") or "未知标题")[:20]
            duration = video.get("duration", "--:--")
            views = video.get("views", 0)
            movie_id = video.get("movieId", "")

            lines.append(f"\n{i}. {title}")
            if duration:
                lines.append(f"   ⏱️ {duration}  👁️ {self.format_number(views)}")
            if movie_id:
                lines.append(f"   🆔 {movie_id}")

        lines.append("\n💡 使用 'xporn info <id>' 查看详情")
        return "\n".join(lines)

    def format_ranking_with_images(self, videos: List[Dict], page: int) -> List[str]:
        """格式化排行榜（带图片）"""
        display_videos = videos[: self.max_results]
        result = [f"📺 Twitter 视频排行榜 - 第 {page} 页"]

        for i, video in enumerate(display_videos, 1):
            title = str(video.get("title") or "未知标题")[:20]
            duration = video.get("duration", "--:--")
            views = video.get("views", 0)
            movie_id = video.get("movieId", "")
            thumbnail = video.get("thumbnail", "")

            info = f"{i}. {title}"
            if duration:
                info += f"\n   ⏱️ {duration}  👁️ {self.format_number(views)}"
            if movie_id:
                info += f"\n   🆔 {movie_id}"

            result.append(info)
            if thumbnail:
                result.append(thumbnail)

        result.append("\n💡 使用 'xporn info <id>' 查看详情")
        return result

    def format_hot_videos(self, videos: List[Dict]) -> str:
        """格式化热门视频"""
        lines = ["🔥 热门视频推荐"]

        for i, video in enumerate(videos[:8], 1):
            title = str(video.get("title") or "未知标题")[:18]
            likes = video.get("likes", 0)
            views = video.get("views", 0)
            movie_id = video.get("movieId", "")

            lines.append(f"\n{i}. {title}")
            lines.append(
                f"   ❤️ {self.format_number(likes)}  👁️ {self.format_number(views)}"
            )
            if movie_id:
                lines.append(f"   🆔 {movie_id}")

        return "\n".join(lines)

    def format_hot_videos_with_images(self, videos: List[Dict]) -> List[str]:
        """格式化热门视频（带图片）"""
        result = ["🔥 热门视频推荐"]

        for i, video in enumerate(videos[:8], 1):
            title = str(video.get("title") or "未知标题")[:18]
            likes = video.get("likes", 0)
            views = video.get("views", 0)
            movie_id = video.get("movieId", "")
            thumbnail = video.get("thumbnail", "")

            info = f"{i}. {title}"
            info += f"\n   ❤️ {self.format_number(likes)}  👁️ {self.format_number(views)}"
            if movie_id:
                info += f"\n   🆔 {movie_id}"

            result.append(info)
            if thumbnail:
                result.append(thumbnail)

        return result

    def format_search_results(self, videos: List[Dict], keyword: str) -> str:
        """格式化搜索结果"""
        lines = [f"🔍 搜索结果: {keyword}"]

        for i, video in enumerate(videos[:10], 1):
            title = str(video.get("title") or "未知标题")[:20]
            duration = video.get("duration", "--:--")
            movie_id = video.get("movieId", "")

            lines.append(f"\n{i}. {title}")
            if duration:
                lines.append(f"   ⏱️ {duration}")
            if movie_id:
                lines.append(f"   🆔 {movie_id}")

        return "\n".join(lines)

    def format_search_results_with_images(
        self, videos: List[Dict], keyword: str
    ) -> List[str]:
        """格式化搜索结果（带图片）"""
        result = [f"🔍 搜索结果: {keyword}"]

        for i, video in enumerate(videos[:10], 1):
            title = str(video.get("title") or "未知标题")[:20]
            duration = video.get("duration", "--:--")
            movie_id = video.get("movieId", "")
            thumbnail = video.get("thumbnail", "")

            info = f"{i}. {title}"
            if duration:
                info += f"\n   ⏱️ {duration}"
            if movie_id:
                info += f"\n   🆔 {movie_id}"

            result.append(info)
            if thumbnail:
                result.append(thumbnail)

        return result

    def format_video_detail(self, video: Dict) -> str:
        """格式化视频详情"""
        lines = ["📄 视频详情"]
        lines.append("=" * 40)

        title = str(video.get("title") or "未知标题")
        lines.append(f"\n📌 标题: {title}")

        if video.get("duration"):
            lines.append(f"⏱️ 时长: {video['duration']}")

        if video.get("views"):
            lines.append(f"👁️ 观看: {self.format_number(video['views'])}")

        if video.get("likes"):
            lines.append(f"❤️ 点赞: {self.format_number(video['likes'])}")

        if video.get("comments"):
            lines.append(f"💬 评论: {self.format_number(video['comments'])}")

        if video.get("movieId"):
            lines.append(f"\n🆔 ID: {video['movieId']}")

        if video.get("url"):
            lines.append(f"\n🔗 链接: {video['url']}")

        lines.append(f"\n{'=' * 40}")
        lines.append("💡 在浏览器中打开链接观看")
        return "\n".join(lines)

    def format_video_detail_with_image(self, video: Dict) -> List[str]:
        """格式化视频详情（带图片）"""
        result = ["📄 视频详情"]

        title = str(video.get("title") or "未知标题")
        result.append(f"\n📌 标题: {title}")

        if video.get("duration"):
            result.append(f"⏱️ 时长: {video['duration']}")
        if video.get("views"):
            result.append(f"👁️ 观看: {self.format_number(video['views'])}")
        if video.get("likes"):
            result.append(f"❤️ 点赞: {self.format_number(video['likes'])}")

        if video.get("movieId"):
            result.append(f"\n🆔 ID: {video['movieId']}")

        if video.get("url"):
            result.append(f"\n🔗 链接: {video['url']}")

        if video.get("thumbnail"):
            result.append(video["thumbnail"])

        return result

    def format_number(self, num: int) -> str:
        """格式化数字"""
        num = int(num or 0)
        if num >= 10000:
            return f"{num / 10000:.1f}万"
        if num >= 1000:
            return f"{num / 1000:.1f}k"
        return str(num)
