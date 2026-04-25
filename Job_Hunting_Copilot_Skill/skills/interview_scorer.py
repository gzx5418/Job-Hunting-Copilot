"""
面试评估 Skill (Interview Scorer Skill)
AutoClaw Skill ID: interview_scorer

职责：
  对用户的面试回答进行四维评分，
  输出评分、维度分析、改进建议和示范回答。

触发场景：
  - 面试练习 Pipeline 中，用户提交回答后自动触发
  - 或当用户说"帮我评估一下这段面试回答"

GLM 调度方式：
  GLM 将 question + answer + reference_points 传入此 Skill 的 run() 方法。

架构说明：
  本 Skill 属于「语义密集型」任务，需要理解回答内容并评估质量。
  当前提供基于关键词匹配和结构检查的规则评分实现。
  生产环境中由 GLM 完成语义级评分。

  注意：当前规则评分仅作为占位实现，可通过堆砌关键词/长度获得较高分数，
  不具备真正的语义理解能力。上线前需替换为 GLM 语义评分。
"""

import re
import logging
from typing import List, Dict, Any
from skills import AutoClawSkill

DIMENSIONS = {
    "completeness": {"weight": 0.30, "name": "内容完整度"},
    "logic": {"weight": 0.25, "name": "逻辑条理性"},
    "star_structure": {"weight": 0.25, "name": "STAR 结构性"},
    "keyword_coverage": {"weight": 0.20, "name": "关键词覆盖"},
}


class InterviewScorerSkill(AutoClawSkill):
    """
    面试评估 Skill
    四维评分体系评估面试回答质量
    """

    SKILL_NAME = "interview_scorer"
    SKILL_DESCRIPTION = "对面试回答进行四维评分（完整度/条理性/STAR/关键词），输出改进建议。"

    def run(self, question: str, answer: str,
            reference_points: List[str] = None,
            target_role: str = "", **kwargs) -> Dict[str, Any]:
        """
        评估面试回答。

        :param question: 面试题目
        :param answer: 用户的回答文本
        :param reference_points: 参考答案要点列表
        :param target_role: 目标岗位（用于关键词匹配）
        :return: 评分结果 + 改进建议
        """
        self.validate_input({"question": question, "answer": answer}, ["question", "answer"])

        if not answer or len(answer.strip()) < 10:
            return self._error("回答内容过短（至少10个字符）", detail=f"当前长度: {len(answer.strip())}")

        self.logger.info(f"开始面试评估 | 题目: {question[:30]}... | 回答长度: {len(answer)}")

        reference_points = reference_points or []

        dim_scores = {
            "completeness": self._score_completeness(answer, reference_points),
            "logic": self._score_logic(answer),
            "star_structure": self._score_star(answer),
            "keyword_coverage": self._score_keywords(answer, reference_points, target_role),
        }

        total_score = sum(
            dim_scores[k] * DIMENSIONS[k]["weight"] for k in DIMENSIONS
        )
        total_score = round(total_score)

        feedback = self._generate_feedback(dim_scores, answer, question)
        improved_answer = self._generate_improved_answer(question, answer, reference_points)

        tier = self._get_tier(total_score)

        self.logger.info(f"评估完成 | 总分: {total_score} | Tier: {tier}")

        return self._success(
            data={
                "score": total_score,
                "tier": tier,
                "dimensions": {
                    k: {"score": v, "name": DIMENSIONS[k]["name"],
                        "comment": self._dim_comment(k, v)}
                    for k, v in dim_scores.items()
                },
                "feedback": feedback,
                "improved_answer": improved_answer,
            },
            message=f"面试回答评估完成 | 得分: {total_score}/100 | 等级: {tier}"
        )

    def _score_completeness(self, answer: str, ref_points: List[str]) -> int:
        """内容完整度：回答覆盖了多少参考要点"""
        if not ref_points:
            if len(answer) > 100:
                return 70
            elif len(answer) > 50:
                return 55
            return 40

        covered = sum(1 for p in ref_points if any(kw in answer for kw in p.split() if len(kw) > 1))
        ratio = covered / len(ref_points) if ref_points else 0
        return min(100, int(ratio * 100) + 20)

    def _score_logic(self, answer: str) -> int:
        """逻辑条理性：基于连接词、段落结构"""
        score = 50

        logic_markers = ["首先", "其次", "然后", "最后", "因此", "所以", "因为",
                         "不过", "但是", "另外", "同时", "一方面", "另一方面"]
        marker_count = sum(1 for m in logic_markers if m in answer)
        score += min(20, marker_count * 5)

        sentences = [s.strip() for s in re.split(r'[。！？\n]', answer) if s.strip()]
        if len(sentences) >= 4:
            score += 15
        elif len(sentences) >= 2:
            score += 8

        if "第一" in answer or "1." in answer or "一是" in answer:
            score += 10

        return min(100, score)

    def _score_star(self, answer: str) -> int:
        """STAR 结构性检查"""
        score = 0

        s_markers = ["背景", "当时", "情况", "场景", "在那", "的时候", "团队"]
        t_markers = ["目标", "任务", "需要", "要求", "负责"]
        a_markers = ["我做了", "我采取", "我主动", "我组织", "我优化", "我设计",
                     "我分析", "我推动", "我负责", "主导", "策划", "推动"]
        r_markers = ["结果", "最终", "提升了", "达到了", "增加了", "节省了",
                     "完成了", "获得了", "降低了", "提高了", "增长了"]

        if any(m in answer for m in s_markers):
            score += 25
        if any(m in answer for m in t_markers):
            score += 25
        if any(m in answer for m in a_markers):
            score += 25
        if any(m in answer for m in r_markers):
            score += 25

        has_numbers = bool(re.search(r'\d+[%％万千百]', answer))
        if has_numbers:
            score = min(100, score + 10)

        return min(100, score)

    def _score_keywords(self, answer: str, ref_points: List[str],
                        target_role: str) -> int:
        """关键词覆盖度"""
        professional_terms = [
            "协作", "沟通", "优化", "分析", "策划", "执行", "驱动",
            "用户", "需求", "产品", "数据", "项目", "团队", "目标",
            "方案", "策略", "流程", "指标", "效果", "成果", "复盘",
        ]

        covered = sum(1 for t in professional_terms if t in answer)
        ratio = covered / len(professional_terms)
        return min(100, int(ratio * 150) + 20)

    def _dim_comment(self, dim: str, score: int) -> str:
        if score >= 80:
            return "表现优秀"
        elif score >= 60:
            return "基本达标，有提升空间"
        elif score >= 40:
            return "需要改进"
        return "存在明显不足"

    def _get_tier(self, score: int) -> str:
        if score >= 90:
            return "S"
        elif score >= 75:
            return "A"
        elif score >= 60:
            return "B"
        elif score >= 40:
            return "C"
        return "D"

    def _generate_feedback(self, dim_scores: Dict[str, int], answer: str,
                           question: str) -> List[str]:
        feedback: List[str] = []

        if dim_scores["completeness"] < 60:
            feedback.append("回答覆盖的要点不够全面，建议先列举关键要点再逐个展开")
        if dim_scores["logic"] < 60:
            feedback.append("逻辑结构较弱，建议使用'首先/其次/最后'或按时间线组织回答")
        if dim_scores["star_structure"] < 60:
            feedback.append("缺少STAR结构，建议按'场景→任务→行动→结果'组织回答")
            if dim_scores["star_structure"] < 30:
                feedback.append("特别缺少量化成果（Result），请补充具体数字和结果")
        if dim_scores["keyword_coverage"] < 60:
            feedback.append("专业术语使用较少，建议多用岗位相关的专业表达")

        if not feedback:
            feedback.append("整体表现不错！继续保持这种回答结构")

        if len(answer) < 80:
            feedback.append("回答偏短，建议展开细节，目标200-400字")

        return feedback

    def _generate_improved_answer(self, question: str, answer: str,
                                  ref_points: List[str]) -> str:
        """生成示范性改进回答框架"""
        points = "；".join(ref_points) if ref_points else "（请根据自身经历补充）"

        return (
            f"【示范回答框架】\n\n"
            f"**场景(S)**: 在[具体时间]，我在[组织/团队]中...\n\n"
            f"**任务(T)**: 我的目标是[明确的任务/挑战]...\n\n"
            f"**行动(A)**: 我采取了以下行动：\n"
            f"  1. [具体行动1，用强动词]\n"
            f"  2. [具体行动2，展示主动性]\n"
            f"  3. [具体行动3，展示协作/创新]\n\n"
            f"**结果(R)**: 最终实现了[量化成果]，例如提升了X% / 覆盖了Y人 / 节省了Z小时...\n\n"
            f"参考要点：{points}"
        )
