"""
亮点打磨 Skill (STAR Polisher Skill)
AutoClaw Skill ID: star_polisher

职责：
  接收结构化的 ExperienceItem 列表，
  按照 STAR 原则（情景、任务、行动、结果）重构每条经历，
  针对目标岗位的 JD 关键词进行精准覆盖，
  使描述具备强烈的职业感与量化结果。

触发场景（内部 Skill，通常由 Pipeline 自动触发）：
  - 在 experience_extractor 执行完毕后自动触发
  - 或当用户说"用STAR原则重写我的经历"

GLM 调度方式：
  GLM 将 experience_extractor 的输出（experiences 列表）
  和 jd_keywords 一并传入此 Skill 的 run() 方法。

架构说明：
  本 Skill 属于「语义密集型」任务，需要将口语化描述转化为职业化表述。
  在 AutoClaw 框架的生产部署中，此类任务由 GLM 大模型直接完成语义级改写；
  当前提供基于规则引擎的本地实现，包含：
    - 岗位能力模型（ROLE_COMPETENCY_MAP）用于匹配关键词权重
    - 口语→职业化词汇映射表（VOCABULARY_MAP）
    - 量化数据占位符自动插入
  当通过 AutoClaw 接入 GLM 后端时，_rewrite_action() 将委托给 GLM 处理。
"""

import re
from typing import List, Dict, Any
from skills import AutoClawSkill


# ------------------------------------------------------------------
# 管培生/校招通用能力模型（按岗位类型扩展）
# ------------------------------------------------------------------
ROLE_COMPETENCY_MAP = {
    "管培生": {
        "core_keywords": ["跨部门协作", "领导力", "问题解决", "学习能力", "敏捷适应"],
        "impact_verbs": ["统筹", "主导", "协调", "推动", "攻克", "完成"],
        "template_focus": "通用管理素质 + 快速学习力"
    },
    "AI 产品实习生": {
        "core_keywords": ["需求文档", "用户调研", "Prompt 调优", "数据分析", "LLM"],
        "impact_verbs": ["设计", "调研", "分析", "优化", "主导", "迭代"],
        "template_focus": "产品感知 + AI 工具应用经验"
    },
    "运营实习生": {
        "core_keywords": ["用户增长", "社群运营", "内容策划", "数据分析", "活动执行"],
        "impact_verbs": ["运营", "策划", "拉新", "维护", "迭代", "推广"],
        "template_focus": "执行力 + 用户视角 + 数据驱动"
    },
    "default": {
        "core_keywords": ["沟通协作", "问题解决", "执行力", "学习能力"],
        "impact_verbs": ["负责", "参与", "完成", "推动", "优化"],
        "template_focus": "通用职场能力"
    }
}

# 口语化 → 职业化词汇映射表
VOCABULARY_MAP = {
    "参与了": "主导参与",
    "帮忙做": "协助完成",
    "学会了": "熟练掌握",
    "写了": "撰写并产出",
    "拉了赞助": "独立拓展商务合作",
    "办了活动": "统筹策划并执行活动",
    "整理表格": "数据整理与清洗分析",
    "回复消息": "即时响应用户诉求",
    "建了群": "搭建并运营社群体系",
    "打杂": "全流程支撑与协助",
    "做了ppt": "制作汇报材料并演讲",
    "发推文": "内容创作与渠道分发",
    "搞活动": "活动全周期策划与落地",
    "组织人": "团队统筹与人员调配",
}


class StarPolisherSkill(AutoClawSkill):
    """
    亮点打磨 Skill
    将结构化的 ExperienceItem → 职业化的 Markdown 简历描述
    """

    SKILL_NAME = "star_polisher"
    SKILL_DESCRIPTION = "用 STAR 原则重构经历描述，对接目标岗位 JD 关键词，输出职业感强的 Markdown。"

    def run(self, experiences: List[Dict], target_role: str = "default",
            jd_keywords: List[str] = None, **kwargs) -> Dict[str, Any]:
        """
        执行 STAR 打磨。

        :param experiences: ExperienceExtractorSkill 输出的经历列表
        :param target_role: 目标岗位名称
        :param jd_keywords: 从 JD 中提取的关键词列表（可选）
        :return: polished_md 格式的 Markdown 字符串 + 关键词覆盖率
        """
        self.validate_input({"experiences": experiences}, ["experiences"])

        # 获取岗位能力模型
        competency = ROLE_COMPETENCY_MAP.get(
            target_role,
            ROLE_COMPETENCY_MAP["default"]
        )
        # 合并 JD 关键词
        all_keywords = competency["core_keywords"] + (jd_keywords or [])

        self.logger.info(f"开始 STAR 打磨，目标岗位：{target_role}，关键词：{all_keywords}")

        polished_blocks = []
        for exp in experiences:
            block = self._polish_single(exp, target_role, competency, all_keywords)
            polished_blocks.append(block)

        polished_md = "\n".join(polished_blocks)
        keyword_coverage = self._calc_coverage(polished_md, all_keywords)

        self.logger.info(f"打磨完成，关键词覆盖率：{keyword_coverage:.0%}")

        return self._success(
            data={
                "polished_md": polished_md,
                "keyword_coverage": keyword_coverage,
                "blocks_count": len(polished_blocks)
            },
            message=f"STAR 打磨完成，关键词覆盖率 {keyword_coverage:.0%}"
        )

    def _polish_single(self, exp: Dict, target_role: str,
                       competency: Dict, keywords: List[str]) -> str:
        """对单条经历进行 STAR 重构"""
        org = exp.get("organization", "某组织")
        role = exp.get("role", "成员")
        time = exp.get("time", "时间待补充")
        raw_actions = exp.get("raw_actions", [])

        header = f"### {org} — {role} | {time}"
        lines = [header]

        # 对每个原始动作进行 STAR 改写
        for action in raw_actions:
            polished_line = self._rewrite_action(action, target_role, competency)
            if polished_line:
                lines.append(f"- {polished_line}")

        # 若没有任何可解析的动作，添加占位引导
        if len(lines) == 1:
            lines.append(f"- **[待补充]**：基于 {org} 的 {role} 经历，请补充具体的行动与量化成果（参考 STAR 原则）。")

        lines.append("")  # 段落间空行
        return "\n".join(lines)

    def _rewrite_action(self, raw_action: str, target_role: str, competency: Dict) -> str:
        """
        将单条口语化行为重写为 STAR 格式的职业描述。
        实际产品中此步骤由 GLM 完成语义理解；
        此处提供规则引擎作为轻量实现。
        """
        if not raw_action or len(raw_action) < 3:
            return ""

        # 词汇替换：口语 → 职业
        rewritten = raw_action
        for colloquial, professional in VOCABULARY_MAP.items():
            rewritten = rewritten.replace(colloquial, professional)

        # 为关键词加粗
        competency_keywords = competency["core_keywords"]
        for kw in competency_keywords:
            rewritten = rewritten.replace(kw, f"**{kw}**")

        # 添加量化占位符（若无数字）
        if not re.search(r'\d+', rewritten):
            rewritten += "（影响范围 **[X]** 人次，提升 **[X]%**，请补充量化数据）"

        return rewritten

    def _calc_coverage(self, polished_md: str, keywords: List[str]) -> float:
        """计算关键词在打磨后内容中的覆盖率"""
        if not keywords:
            return 1.0
        covered = sum(1 for kw in keywords if kw in polished_md)
        return covered / len(keywords)
