"""
文献提炼 Skill (Paper Digest Skill)
AutoClaw Skill ID: paper_digest

职责：
  接收学术论文列表（来自 academic_search），
  对每篇论文的摘要进行结构化提取（核心观点、方法论、结论），
  输出文献综述 Markdown 文本。

触发场景（通常由 Pipeline 自动触发）：
  - 在 academic_search 执行完毕后自动触发

GLM 调度方式：
  GLM 将 papers 列表传入此 Skill 的 run() 方法。

架构说明：
  本 Skill 属于「语义密集型」任务，需要理解论文摘要并提取关键信息。
  在 AutoClaw 生产环境中，由 GLM 完成语义级提炼；
  当前提供基于规则的本地 Demo 实现。
"""

import re
from typing import List, Dict, Any
from skills import AutoClawSkill


class PaperDigestSkill(AutoClawSkill):
    """
    文献提炼 Skill
    对论文摘要进行结构化提取，生成文献综述 Markdown
    """

    SKILL_NAME = "paper_digest"
    SKILL_DESCRIPTION = "对学术论文列表进行结构化提炼，提取核心观点、方法论、结论，生成综述 Markdown。"

    # 关键方法/方向识别关键词
    METHOD_KEYWORDS = {
        "transformer": "Transformer 架构",
        "deep learning": "深度学习方法",
        "reinforcement learning": "强化学习方法",
        "prompt": "Prompt 工程",
        "fine-tun": "微调方法",
        "multi-agent": "多智能体协作",
        "survey": "综述方法",
        "benchmark": "基准测试评估",
        "experiment": "实验验证",
        "systematic review": "系统性综述",
        "LLM": "大语言模型",
        "GPT": "GPT 系列模型",
        "BERT": "BERT 系列模型",
    }

    # 结果/数据识别模式
    RESULT_PATTERN = re.compile(
        r'(\d+(?:\.\d+)?)\s*%'
        r'|提升.*?(\d+(?:\.\d+)?)\s*%'
        r'|提高了?\s*(\d+(?:\.\d+)?)\s*%'
        r'|F1.*?(\d+(?:\.\d+)?)'
        r'|准确率.*?(\d+(?:\.\d+)?)\s*%'
        r'|超越.*?(\d+(?:\.\d+)?)\s*%?',
        re.IGNORECASE
    )

    def run(self, papers: List[Dict], research_topic: str = "",
            **kwargs) -> Dict[str, Any]:
        """
        执行文献提炼。

        :param papers: academic_search 输出的论文列表
        :param research_topic: 研究主题（用于综述标题）
        :return: 结构化文献综述 Markdown + 趋势分析
        """
        self.validate_input({"papers": papers}, ["papers"])

        self.logger.info(f"开始文献提炼 | 论文数: {len(papers)} | 主题: {research_topic}")

        digested = []
        for paper in papers:
            item = self._digest_single(paper)
            digested.append(item)

        # 生成综述 Markdown
        review_md = self._build_review_markdown(digested, research_topic)

        # 趋势分析
        trends = self._analyze_trends(digested)

        self.logger.info(f"文献提炼完成 | 提取 {len(digested)} 篇 | 趋势: {len(trends)} 条")

        return self._success(
            data={
                "digested_papers": digested,
                "review_md": review_md,
                "trends": trends,
                "paper_count": len(digested),
                "topic": research_topic,
            },
            message=f"完成 {len(digested)} 篇文献的结构化提炼"
        )

    def _digest_single(self, paper: Dict) -> Dict:
        """对单篇论文进行结构化提取"""
        abstract = paper.get("abstract", "")
        title = paper.get("title", "无标题")

        return {
            "title": title,
            "authors": paper.get("authors", "未知"),
            "year": paper.get("year"),
            "citations": paper.get("citations", 0),
            "url": paper.get("url", ""),
            "source": paper.get("source", "unknown"),
            "core_methods": self._extract_methods(abstract),
            "key_findings": self._extract_findings(abstract),
            "conclusion": self._extract_conclusion(abstract),
        }

    def _extract_methods(self, text: str) -> List[str]:
        """从摘要中提取方法关键词"""
        found = []
        text_lower = text.lower()
        for keyword, label in self.METHOD_KEYWORDS.items():
            if keyword.lower() in text_lower:
                found.append(label)
        return found or ["方法论需进一步分析"]

    def _extract_findings(self, text: str) -> List[str]:
        """从摘要中提取关键发现（量化数据）"""
        findings = []
        matches = self.RESULT_PATTERN.findall(text)
        if matches:
            for match_group in matches:
                for m in match_group:
                    if m:
                        findings.append(f"关键指标: {m}%")
        if not findings:
            # 提取摘要的前两句作为发现
            sentences = re.split(r'[。.；;]', text)
            if len(sentences) >= 2:
                findings.append(sentences[1].strip()[:100])
        return findings or ["具体数据需阅读全文"]

    def _extract_conclusion(self, text: str) -> str:
        """提取结论（摘要最后部分）"""
        sentences = re.split(r'[。.]', text)
        if len(sentences) >= 3:
            return sentences[-1].strip()[:200] if sentences[-1].strip() else sentences[-2].strip()[:200]
        return text[-150:] if len(text) > 150 else text

    def _build_review_markdown(self, digested: List[Dict], topic: str) -> str:
        """生成文献综述 Markdown"""
        lines = [f"# {topic} -- 文献综述报告\n"]
        lines.append(f"共调研 **{len(digested)}** 篇相关论文。\n")

        for i, paper in enumerate(digested, 1):
            year = paper.get("year", "N/A")
            citations = paper.get("citations", 0)
            lines.append(f"## {i}. {paper['title']}")
            lines.append(f"- 作者: {paper['authors']} | 年份: {year} | 引用: {citations}")
            methods = paper.get("core_methods", [])
            if methods:
                lines.append(f"- 方法: {', '.join(methods)}")
            findings = paper.get("key_findings", [])
            if findings:
                lines.append(f"- 发现: {'; '.join(findings[:3])}")
            lines.append(f"- 结论: {paper.get('conclusion', '需进一步分析')}")
            if paper.get("url"):
                lines.append(f"- 链接: {paper['url']}")
            lines.append("")

        return "\n".join(lines)

    def _analyze_trends(self, digested: List[Dict]) -> List[str]:
        """分析研究趋势"""
        trends = []

        # 按年份统计
        years = [p["year"] for p in digested if p.get("year")]
        if years:
            recent = sorted(years, reverse=True)
            trends.append(f"最新研究年份: {recent[0]}，覆盖 {min(years)}-{max(years)}")

        # 按引用数排名
        by_citations = sorted(digested, key=lambda x: x.get("citations", 0), reverse=True)
        if by_citations:
            top = by_citations[0]
            trends.append(f"最高引用论文: 「{top['title'][:40]}...」({top.get('citations', 0)} 次)")

        # 按方法聚类
        all_methods = []
        for p in digested:
            all_methods.extend(p.get("core_methods", []))
        if all_methods:
            from collections import Counter
            method_counts = Counter(all_methods)
            top_methods = method_counts.most_common(3)
            trends.append(f"主流方法: {', '.join([m[0] for m in top_methods])}")

        return trends
