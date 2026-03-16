"""
Web Search Skill - Search the web and fetch content
"""

from ada.skill.base import Skill, SkillMetadata, SkillContext, SkillResult
from typing import Dict, Any, List, Optional
import asyncio
import urllib.parse
import json


class WebSearchSkill(Skill):
    """
    Skill for web search and content retrieval.

    Capabilities:
    - Web search via search engines
    - URL content fetching
    - Information extraction
    """

    metadata = SkillMetadata(
        id="builtin.web.search",
        name="网络搜索",
        version="1.0.0",
        description="搜索互联网、获取网页内容",
        author="Ada Team",
        category="information",
        tags=["web", "search", "internet", "url", "网络", "搜索", "网址"],
        permissions=["network.request"],
        examples=[
            "搜索 Python 教程",
            "查一下今天的新闻",
            "打开 https://example.com",
            "帮我找找关于 AI 的文章"
        ]
    )

    # Search engine configurations
    SEARCH_ENGINES = {
        "google": "https://www.google.com/search?q={}",
        "bing": "https://www.bing.com/search?q={}",
        "duckduckgo": "https://duckduckgo.com/?q={}",
        "baidu": "https://www.baidu.com/s?wd={}",
    }

    def __init__(self):
        self._default_engine = "duckduckgo"

    def can_handle(self, context: SkillContext) -> float:
        """Check if this skill matches"""
        search_keywords = [
            "搜索", "查找", "查一下", "帮我找", "搜索一下",
            "search", "find", "look up", "google"
        ]
        url_keywords = ["http://", "https://", "www.", "打开链接", "open url"]

        user_input = context.user_input.lower()
        score = 0.0

        for kw in search_keywords:
            if kw in user_input:
                score += 0.4

        for kw in url_keywords:
            if kw in user_input:
                score += 0.5

        return min(score, 1.0)

    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute web search or fetch"""
        user_input = context.user_input
        entities = context.entities

        # Check if it's a URL
        if self._is_url(user_input):
            return await self._fetch_url(user_input)

        # Extract search query
        query = self._extract_query(user_input, entities)

        if not query:
            return SkillResult.fail("请提供搜索内容")

        # Check if should open in browser or fetch results
        if "打开" in user_input or "open" in user_input.lower():
            return await self._open_search(query)
        else:
            return await self._search_and_summarize(query)

    def _is_url(self, text: str) -> bool:
        """Check if text contains a URL"""
        return any(proto in text.lower() for proto in ["http://", "https://", "www."])

    def _extract_url(self, text: str) -> Optional[str]:
        """Extract URL from text"""
        import re

        # Match URLs
        patterns = [
            r'https?://[^\s<>"{}|\\^`\[\]]+',
            r'www\.[^\s<>"{}|\\^`\[\]]+\.[a-z]{2,}',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                url = match.group(0)
                if not url.startswith("http"):
                    url = "https://" + url
                return url

        return None

    def _extract_query(self, text: str, entities: Dict) -> Optional[str]:
        """Extract search query from text"""
        import re

        # Pattern patterns to remove
        patterns = [
            r"^(?:搜索|查找|查一下|帮我找|搜索一下|search\s+(?:for\s+)?)\s*",
            r"\s*(?:吧|吗|呢)$",
        ]

        query = text.strip()

        for pattern in patterns:
            query = re.sub(pattern, "", query, flags=re.IGNORECASE)

        return query.strip() if query.strip() else None

    async def _open_search(self, query: str) -> SkillResult:
        """Open search in browser"""
        import subprocess

        encoded_query = urllib.parse.quote(query)
        url = self.SEARCH_ENGINES[self._default_engine].format(encoded_query)

        try:
            subprocess.run(["xdg-open", url], check=True, capture_output=True)
            return SkillResult.ok(
                message=f"已在浏览器中打开搜索: {query}",
                output={"url": url, "query": query}
            )
        except Exception as e:
            return SkillResult.fail(f"无法打开浏览器: {e}")

    async def _search_and_summarize(self, query: str) -> SkillResult:
        """Search and return summarized results"""
        # This would ideally use a search API or web scraper
        # For now, return a helpful message

        encoded_query = urllib.parse.quote(query)
        urls = {
            engine: template.format(encoded_query)
            for engine, template in self.SEARCH_ENGINES.items()
        }

        return SkillResult.ok(
            message=f"搜索 '{query}' 的链接:\n" +
                   "\n".join(f"  {engine}: {url}" for engine, url in urls.items()),
            output={"query": query, "urls": urls}
        )

    async def _fetch_url(self, text: str) -> SkillResult:
        """Fetch and summarize URL content"""
        url = self._extract_url(text)

        if not url:
            return SkillResult.fail("无法识别网址")

        try:
            # Try to fetch content
            content = await self._fetch_content(url)

            if content:
                # Summarize content
                summary = self._summarize_content(content)

                return SkillResult.ok(
                    message=f"获取到 {url} 的内容:\n{summary}",
                    output={"url": url, "content": content[:5000]}
                )
            else:
                # Open in browser instead
                import subprocess
                subprocess.run(["xdg-open", url], capture_output=True)
                return SkillResult.ok(
                    message=f"已在浏览器中打开: {url}",
                    output={"url": url}
                )

        except Exception as e:
            return SkillResult.fail(f"获取内容失败: {e}")

    async def _fetch_content(self, url: str) -> Optional[str]:
        """Fetch content from URL"""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        content_type = response.headers.get("Content-Type", "")

                        if "text/html" in content_type:
                            html = await response.text()
                            return self._extract_text_from_html(html)
                        elif "text/" in content_type:
                            return await response.text()

            return None

        except Exception as e:
            return None

    def _extract_text_from_html(self, html: str) -> str:
        """Extract readable text from HTML"""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, 'html.parser')

            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()

            # Get text
            text = soup.get_text(separator='\n')

            # Clean up
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            return text[:10000]  # Limit size

        except ImportError:
            # Fallback without BeautifulSoup
            import re
            text = re.sub(r'<[^>]+>', '', html)
            text = re.sub(r'\s+', ' ', text)
            return text[:10000]

    def _summarize_content(self, content: str, max_length: int = 500) -> str:
        """Create a brief summary of content"""
        # Simple summarization - take first few paragraphs
        paragraphs = content.split('\n\n')
        summary_parts = []
        current_length = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if current_length + len(para) > max_length:
                break

            summary_parts.append(para)
            current_length += len(para)

        return '\n\n'.join(summary_parts)
