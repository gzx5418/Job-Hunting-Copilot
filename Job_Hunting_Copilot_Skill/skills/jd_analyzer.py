"""
JD 分析 Skill (JD Analyzer Skill)
AutoClaw Skill ID: jd_analyzer

职责：
  接收目标岗位的 JD（Job Description）文本，
  提取硬技能要求、软素质要求、核心关键词，
  为 star_polisher 和 match_scorer 提供 JD 洞察数据。

触发场景：
  - 在简历生成流程中，用户指定目标岗位后自动触发
  - 或当用户说"帮我分析这个岗位的JD"

GLM 调度方式：
  GLM 将 jd_text 和 target_role 传入此 Skill 的 run() 方法。

架构说明：
  本 Skill 属于「语义密集型」任务，需要从自然语言 JD 中提取结构化信息。
  在 AutoClaw 框架的生产部署中，JD 分析由 GLM 大模型直接完成；
  当前提供基于关键词匹配和正则的本地实现。
"""

import re
from typing import List, Dict, Any, Optional
from skills import AutoClawSkill


# 常见技能关键词库（按类别分组）
SKILL_CATEGORIES = {
    "编程语言": [
        "Python", "Java", "JavaScript", "TypeScript", "C++", "Go", "Rust",
        "SQL", "R", "MATLAB", "Shell", "Bash",
    ],
    "AI/数据": [
        "机器学习", "深度学习", "NLP", "CV", "LLM", "Prompt", "TensorFlow",
        "PyTorch", "scikit-learn", "pandas", "numpy", "数据分析", "数据挖掘",
        "A/B测试", "数据可视化", "Prompt Engineering",
    ],
    "产品工具": [
        "Axure", "Figma", "墨刀", "Sketch", "Xmind", "Visio",
        "PRD", "原型设计", "需求文档", "竞品分析", "用户调研",
    ],
    "通用软技能": [
        "沟通能力", "团队协作", "项目管理", "问题解决", "学习能力",
        "抗压能力", "责任心", "主动性", "跨部门协作", "自驱力",
    ],
}

# 常见学历要求模式
DEGREE_PATTERNS = {
    "本科及以上": [r"本科", r"学士学位", r"Bachelor"],
    "硕士及以上": [r"硕士", r"研究生", r"Master", r"研一", r"研二"],
    "不限": [r"学历不限", r"不限学历"],
}

# 常见出勤要求模式
AVAILABILITY_PATTERNS = [
    (r"每周\s*(\d)\s*天", "days_per_week"),
    (r"(\d+)\s*个?月(?:以上)?", "months"),
    (r"全职|full[- ]?time", "full_time"),
    (r"实习", "internship"),
]


class JDAnalyzerSkill(AutoClawSkill):
    """
    JD 分析 Skill
    从岗位描述文本中提取结构化要求信息
    """

    SKILL_NAME = "jd_analyzer"
    SKILL_DESCRIPTION = "从岗位 JD 文本中提取硬技能、软素质、学历、出勤要求等结构化信息。"

    def run(self, jd_text: str, target_role: str = "",
            **kwargs) -> Dict[str, Any]:
        """
        执行 JD 分析。

        :param jd_text: 岗位 JD 文本
        :param target_role: 目标岗位名称
        :return: 结构化的 JD 分析结果
        """
        self.validate_input({"jd_text": jd_text}, ["jd_text"])

        self.logger.info(f"开始 JD 分析 | 目标岗位: {target_role or '未指定'}")

        jd_text_lower = jd_text.lower()

        # 1. 提取硬技能
        hard_skills = self._extract_skills(jd_text, jd_text_lower)

        # 2. 提取软素质
        soft_skills = self._extract_soft_skills(jd_text, jd_text_lower)

        # 3. 提取学历要求
        degree_req = self._extract_degree(jd_text)

        # 4. 提取出勤要求
        availability_req = self._extract_availability(jd_text)

        # 5. 提取核心关键词（供 star_polisher 使用）
        core_keywords = hard_skills + soft_skills

        # 6. 生成 JD 摘要
        jd_summary = self._generate_summary(
            target_role, hard_skills, soft_skills, degree_req, availability_req
        )

        result_data = {
            "jd_keywords": core_keywords,
            "jd_hard_skills": hard_skills,
            "jd_soft_skills": soft_skills,
            "jd_degree_req": degree_req,
            "jd_availability_req": availability_req,
            "jd_summary": jd_summary,
            "target_role": target_role,
        }

        self.logger.info(
            f"JD 分析完成 | 硬技能: {len(hard_skills)} | "
            f"软素质: {len(soft_skills)} | 学历: {degree_req}"
        )

        return self._success(
            data=result_data,
            message=f"JD 分析完成，提取 {len(core_keywords)} 个关键词"
        )

    def _extract_skills(self, text: str, text_lower: str) -> List[str]:
        """从 JD 中提取硬技能"""
        found = []
        for category, skills in SKILL_CATEGORIES.items():
            if category == "通用软技能":
                continue
            for skill in skills:
                if skill.lower() in text_lower:
                    found.append(skill)
        return found

    def _extract_soft_skills(self, text: str, text_lower: str) -> List[str]:
        """从 JD 中提取软素质"""
        soft_skills = SKILL_CATEGORIES["通用软技能"]
        found = []
        for skill in soft_skills:
            if skill in text or skill.lower() in text_lower:
                found.append(skill)
        # 额外模式匹配
        extra_patterns = {
            "抗压能力": [r"抗压", r"快节奏", r"高强度", r"加班"],
            "自驱力": [r"自驱", r"主动", r"自我驱动"],
            "跨部门协作": [r"跨部门", r"跨团队", r"协调.*部门"],
        }
        for skill, patterns in extra_patterns.items():
            if skill not in found:
                for p in patterns:
                    if re.search(p, text):
                        found.append(skill)
                        break
        return found

    def _extract_degree(self, text: str) -> str:
        """提取学历要求"""
        for degree, patterns in DEGREE_PATTERNS.items():
            for p in patterns:
                if re.search(p, text, re.IGNORECASE):
                    return degree
        return "未明确要求"

    def _extract_availability(self, text: str) -> Dict[str, Any]:
        """提取出勤要求"""
        result = {"raw": "未明确"}
        for pattern, key in AVAILABILITY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if key == "days_per_week":
                    result["days_per_week"] = int(match.group(1))
                elif key == "months":
                    result["months"] = int(match.group(1))
                elif key == "full_time":
                    result["full_time"] = True
                elif key == "internship":
                    result["internship"] = True
        parts = []
        if "days_per_week" in result:
            parts.append(f"每周{result['days_per_week']}天")
        if "months" in result:
            parts.append(f"至少{result['months']}个月")
        if "full_time" in result:
            parts.append("全职")
        if parts:
            result["raw"] = "、".join(parts)
        return result

    def _generate_summary(self, target_role: str, hard_skills: List[str],
                          soft_skills: List[str], degree: str,
                          availability: Dict) -> str:
        """生成 JD 摘要文本"""
        parts = []
        if target_role:
            parts.append(f"目标岗位: {target_role}")
        if hard_skills:
            parts.append(f"核心技能: {', '.join(hard_skills[:6])}")
        if soft_skills:
            parts.append(f"软素质: {', '.join(soft_skills[:4])}")
        if degree != "未明确要求":
            parts.append(f"学历: {degree}")
        avail_raw = availability.get("raw", "未明确")
        if avail_raw != "未明确":
            parts.append(f"出勤: {avail_raw}")
        return " | ".join(parts)
