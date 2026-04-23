"""
经历萃取 Skill (Experience Extractor Skill)
AutoClaw Skill ID: experience_extractor

职责：
  从用户提供的非结构化文本（经历草稿、证书描述）中，
  提取时间、组织、角色、核心成就等关键信息，
  结构化输出为标准的 ExperienceItem 列表。

触发场景：
  - "这是我大学四年的经历草稿"
  - "帮我整理一下这些经历"
  - "从这段文字里提取我做过的事"

GLM 调度方式：
  由 GLM 识别用户意图后，自动调用此 Skill 的 run() 方法，
  并将结构化结果传递给下一个 Skill（StarPolisher）。
"""

import re
from typing import List, Dict, Any
from skills import AutoClawSkill


class ExperienceExtractorSkill(AutoClawSkill):
    """
    经历萃取 Skill
    将非结构化文本 → 结构化的 ExperienceItem 列表
    """

    SKILL_NAME = "experience_extractor"
    SKILL_DESCRIPTION = "从非结构化经历草稿中提取时间、角色、核心成就，为 STAR 打磨做准备。"

    # 时间格式识别模式
    TIME_PATTERNS = [
        r'\d{4}[.\-/年]\d{1,2}[.\-/月]?\s*[-~至到]\s*\d{4}[.\-/年]\d{1,2}',
        r'\d{4}[.\-/年]\d{1,2}[.\-/月]?\s*[-~至到]\s*(?:至今|现在|present)',
        r'\d{4}年?\s*[-~]\s*\d{4}年?',
    ]

    # 组织/角色高频关键词
    ROLE_KEYWORDS = [
        '负责人', '干事', '部长', '会长', '组长', '主席',
        '实习生', '助理', '专员', '经理', '成员', '主持人',
        'intern', 'leader', 'PM', 'TA'
    ]

    ORG_KEYWORDS = [
        '学生会', '社团', '协会', '部门', '公司', '团队',
        '项目组', '研究室', '实验室', '创业', '班级'
    ]

    def run(self, raw_text: str, target_role: str = "", **kwargs) -> Dict[str, Any]:
        """
        执行经历萃取。

        :param raw_text: 用户输入的原始经历草稿文本
        :param target_role: 目标岗位（用于过滤无关经历）
        :return: 结构化的 experiences 列表
        """
        self.validate_input({"raw_text": raw_text}, ["raw_text"])

        self.logger.info(f"开始萃取经历，目标岗位：{target_role or '未指定'}")
        self.logger.info(f"输入文本长度：{len(raw_text)} 字符")

        experiences = self._extract_segments(raw_text)

        if not experiences:
            # 如果无法自动分段，将整段作为一条经历
            experiences = [{
                "time": self._extract_time(raw_text) or "时间待补充",
                "organization": self._extract_organization(raw_text) or "组织待补充",
                "role": self._extract_role(raw_text) or "角色待补充",
                "raw_actions": self._extract_raw_actions(raw_text),
                "source": "整段提取"
            }]

        self.logger.info(f"成功萃取 {len(experiences)} 段经历")

        return self._success(
            data={"experiences": experiences, "count": len(experiences)},
            message=f"成功从草稿中萃取出 {len(experiences)} 段结构化经历"
        )

    def _extract_segments(self, text: str) -> List[Dict]:
        """
        尝试将文本分割为多段独立经历
        分割标志：时间段、换行+序号、明显的组织名称
        """
        segments = []

        # 策略1：按双换行分段
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        # 如果只有一段，按句号分割再合并
        if len(paragraphs) <= 1:
            sentences = re.split(r'[。；\n]', text)
            paragraphs = []
            buffer = []
            for s in sentences:
                buffer.append(s.strip())
                if any(k in s for k in self.ORG_KEYWORDS + self.ROLE_KEYWORDS):
                    if len(buffer) > 1:
                        paragraphs.append('。'.join(buffer[:-1]))
                    buffer = [s]
            if buffer:
                paragraphs.append('。'.join(buffer))

        for para in paragraphs:
            if not para or len(para) < 10:
                continue
            segment = {
                "time": self._extract_time(para) or "时间待补充",
                "organization": self._extract_organization(para) or "组织待补充",
                "role": self._extract_role(para) or "成员",
                "raw_actions": self._extract_raw_actions(para),
                "source": "自动分段"
            }
            segments.append(segment)

        return segments

    def _extract_time(self, text: str) -> str:
        """提取时间段"""
        for pattern in self.TIME_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group().strip()
        # 尝试提取单个年份
        year_match = re.search(r'\d{4}年?', text)
        if year_match:
            return year_match.group()
        return ""

    def _extract_organization(self, text: str) -> str:
        """提取组织/公司名称"""
        for keyword in self.ORG_KEYWORDS:
            idx = text.find(keyword)
            if idx != -1:
                # 提取关键词前后的词语作为组织名
                start = max(0, idx - 8)
                end = min(len(text), idx + len(keyword) + 5)
                return text[start:end].strip('，。； ')
        return ""

    def _extract_role(self, text: str) -> str:
        """提取角色"""
        for keyword in self.ROLE_KEYWORDS:
            if keyword in text:
                idx = text.find(keyword)
                start = max(0, idx - 5)
                end = min(len(text), idx + len(keyword))
                return text[start:end].strip('，。：: ')
        return ""

    def _extract_raw_actions(self, text: str) -> List[str]:
        """提取原始行为描述，拆分为动作列表"""
        # 清洗时间和组织信息后剩余的内容作为行为
        cleaned = re.sub(r'\d{4}[.\-/年]\d{1,2}[.\-/月]?\s*[-~至到]\s*\S+', '', text)
        for kw in self.ORG_KEYWORDS + self.ROLE_KEYWORDS:
            cleaned = cleaned.replace(kw, '')

        # 按逗号/顿号/分号分割行为
        actions = re.split(r'[，,；;、]', cleaned)
        actions = [a.strip().strip('。') for a in actions if a.strip() and len(a.strip()) > 3]
        return actions[:8]  # 最多保留8条行为
