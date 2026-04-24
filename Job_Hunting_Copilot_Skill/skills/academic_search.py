"""
学术搜索 Skill (Academic Search Skill)
AutoClaw Skill ID: academic_search

职责：
  根据研究主题关键词，调用 Semantic Scholar API 搜索学术论文，
  返回论文列表（标题、作者、摘要、年份、引用数）。

触发场景：
  - "帮我调研关于XXX的学术文献"
  - "搜索大语言模型相关的论文"

GLM 调度方式：
  GLM 将 research_topic 传入此 Skill 的 run() 方法。

架构说明：
  使用 Semantic Scholar API（免费、无需 Key）搜索论文。
  在 AutoClaw 生产环境中，可替换为 AutoClaw WebDriver 抓取 Google Scholar。
"""

import json
import logging
from typing import List, Dict, Any, Optional
from urllib.request import urlopen, Request
from urllib.parse import quote
from urllib.error import URLError
from skills import AutoClawSkill

SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"


class AcademicSearchSkill(AutoClawSkill):
    """
    学术搜索 Skill
    根据研究主题搜索学术论文，返回结构化论文列表
    """

    SKILL_NAME = "academic_search"
    SKILL_DESCRIPTION = "根据研究主题搜索学术论文，返回标题、作者、摘要、引用数等结构化数据。"

    def run(self, research_topic: str, max_results: int = 10,
            **kwargs) -> Dict[str, Any]:
        """
        执行学术搜索。

        :param research_topic: 研究主题关键词
        :param max_results: 最大返回论文数
        :return: 结构化论文列表
        """
        self.validate_input({"research_topic": research_topic}, ["research_topic"])

        self.logger.info(f"开始学术搜索 | 主题: {research_topic} | 上限: {max_results}")

        papers = self._search_api(research_topic, max_results)

        if not papers:
            self.logger.warning(f"API 未返回结果，主题: {research_topic}")

        self.logger.info(f"搜索完成，获取 {len(papers)} 篇论文")

        return self._success(
            data={"papers": papers, "total_count": len(papers), "topic": research_topic},
            message=f"搜索到 {len(papers)} 篇相关论文"
        )

    def _search_api(self, topic: str, limit: int) -> List[Dict]:
        """调用 Semantic Scholar API 搜索论文"""
        fields = "title,authors,year,abstract,citationCount,url"
        url = f"{SEMANTIC_SCHOLAR_API}?query={quote(topic)}&limit={limit}&fields={fields}"

        try:
            req = Request(url, headers={"User-Agent": "AutoClaw-Agent/3.0"})
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            papers = []
            for item in data.get("data", []):
                authors = [a.get("name", "") for a in (item.get("authors") or [])]
                papers.append({
                    "title": item.get("title", "无标题"),
                    "authors": ", ".join(authors[:5]),
                    "year": item.get("year"),
                    "abstract": (item.get("abstract") or "无摘要")[:500],
                    "citations": item.get("citationCount", 0),
                    "url": item.get("url", ""),
                    "source": "Semantic Scholar"
                })
            return papers
        except (URLError, json.JSONDecodeError, Exception) as e:
            self.logger.warning(f"API 调用失败: {e}")
            return []
