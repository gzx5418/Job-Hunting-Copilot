"""
学术搜索 Skill (Academic Search Skill)
AutoClaw Skill ID: academic_search

职责：
  根据研究主题关键词，生成学术搜索任务指令，
  由 AutoClaw 的 MCP_WebReader 工具执行搜索，
  返回论文列表（标题、作者、摘要、年份、引用数）。

触发场景：
  - "帮我调研关于XXX的学术文献"
  - "搜索大语言模型相关的论文"

GLM 调度方式：
  GLM 将 research_topic 传入此 Skill 的 run() 方法。

架构说明：
  本 Skill 生成搜索任务指令，由 AutoClaw 框架的 MCP_WebReader 执行。
  不直接调用任何外部 API，完全依赖 AutoClaw 自带能力。
"""

import json
import logging
from typing import List, Dict, Any
from skills import AutoClawSkill


class AcademicSearchSkill(AutoClawSkill):
    """
    学术搜索 Skill
    根据研究主题搜索学术论文，返回结构化论文列表。
    通过 AutoClaw MCP_WebReader 执行搜索，或解析已抓取的网页内容。
    """

    SKILL_NAME = "academic_search"
    SKILL_DESCRIPTION = "根据研究主题搜索学术论文，返回标题、作者、摘要、引用数等结构化数据。"

    def run(self, research_topic: str, max_results: int = 10,
            web_contents: Dict[str, str] = None, **kwargs) -> Dict[str, Any]:
        """
        执行学术搜索。

        :param research_topic: 研究主题关键词
        :param max_results: 最大返回论文数
        :param web_contents: AutoClaw MCP_WebReader 已抓取的网页内容
        :return: 结构化论文列表
        """
        self.validate_input({"research_topic": research_topic}, ["research_topic"])

        self.logger.info(f"开始学术搜索 | 主题: {research_topic} | 上限: {max_results}")

        if web_contents and "search_results" in web_contents:
            papers = self._parse_web_results(web_contents["search_results"], research_topic)
        else:
            papers = []
            task = self._build_search_task(research_topic, max_results)
            self.logger.info(f"已生成 MCP_WebReader 搜索任务，等待执行")

            return self._success(
                data={
                    "status": "pending_web",
                    "web_task": task,
                    "papers": papers,
                    "total_count": 0,
                    "topic": research_topic,
                    "message": "已生成搜索任务，请 MCP_WebReader 执行后重新调用"
                },
                message=f"已生成 [{research_topic}] 的学术搜索任务，等待 AutoClaw MCP_WebReader 执行"
            )

        self.logger.info(f"搜索完成，获取 {len(papers)} 篇论文")

        return self._success(
            data={"papers": papers, "total_count": len(papers), "topic": research_topic},
            message=f"搜索到 {len(papers)} 篇相关论文"
        )

    def _build_search_task(self, topic: str, limit: int) -> Dict:
        """生成 AutoClaw MCP_WebReader 搜索任务指令"""
        return {
            "action": "search_papers",
            "tool": "MCP_WebReader",
            "sources": [
                {
                    "name": "Google Scholar",
                    "url": f"https://scholar.google.com/scholar?q={topic}&hl=zh-CN&num={limit}"
                },
                {
                    "name": "Semantic Scholar",
                    "url": f"https://www.semanticscholar.org/search?q={topic}&sort=relevance"
                }
            ],
            "extract_config": {
                "fields": ["title", "authors", "year", "abstract", "citations", "url"],
                "max_results": limit
            }
        }

    def _parse_web_results(self, content: str, topic: str) -> List[Dict]:
        """解析 AutoClaw MCP_WebReader 返回的搜索结果"""
        papers: List[Dict] = []

        # 尝试解析 JSON 格式
        try:
            data = json.loads(content)
            if isinstance(data, list):
                for item in data[:30]:
                    if not isinstance(item, dict):
                        continue
                    title = item.get("title") or item.get("name") or ""
                    if not title:
                        continue
                    papers.append({
                        "title": title,
                        "authors": item.get("authors", "未知"),
                        "year": item.get("year"),
                        "abstract": (item.get("abstract") or "无摘要")[:500],
                        "citations": item.get("citations", 0),
                        "url": item.get("url", ""),
                        "source": "AutoClaw_MCP_WebReader"
                    })
                return papers
        except (json.JSONDecodeError, TypeError):
            pass

        # 回退到文本块解析
        blocks = [b.strip() for b in content.split('\n\n') if b.strip()]
        for block in blocks[:20]:
            lines = block.split('\n')
            title = lines[0].strip() if lines else ""
            if not title or len(title) < 5:
                continue
            papers.append({
                "title": title,
                "authors": "未知",
                "year": None,
                "abstract": block[:500],
                "citations": 0,
                "url": "",
                "source": "AutoClaw_MCP_WebReader"
            })

        return papers
