"""
面试出题 Skill (Interview Questioner Skill)
AutoClaw Skill ID: interview_questioner

职责：
  根据目标岗位和用户简历，生成结构化面试题，
  支持技术面、行为面、综合面三种类型。

触发场景：
  - "帮我准备管培生面试"
  - "给我出几道AI产品面试题"
  - "模拟面试"

GLM 调度方式：
  GLM 将 target_role 传入此 Skill 的 run() 方法。
  生产环境中，出题逻辑由 GLM 完成语义级生成。

架构说明：
  本 Skill 属于「语义密集型」任务，需要理解岗位需求并设计针对性问题。
  当前提供基于岗位能力模型的规则出题实现。
"""

import os
import json
import random
import logging
from typing import List, Dict, Any
from skills import AutoClawSkill

COMPETENCY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "references", "competency_models"
)


class InterviewQuestionerSkill(AutoClawSkill):
    """
    面试出题 Skill
    根据目标岗位能力模型，生成结构化面试题
    """

    SKILL_NAME = "interview_questioner"
    SKILL_DESCRIPTION = "根据目标岗位和用户简历，生成结构化面试题（技术/行为/综合）。"

    def run(self, target_role: str, resume_data: str = "",
            interview_type: str = "comprehensive",
            num_questions: int = 5, **kwargs) -> Dict[str, Any]:
        """
        生成面试题。

        :param target_role: 目标岗位（如"管培生"）
        :param resume_data: 用户简历文本（可选，用于个性化出题）
        :param interview_type: 面试类型 - behavioral/technical/comprehensive
        :param num_questions: 生成题目数量
        :return: 结构化面试题列表
        """
        self.validate_input({"target_role": target_role}, ["target_role"])

        self.logger.info(
            f"开始面试出题 | 岗位: {target_role} | 类型: {interview_type} | 题数: {num_questions}"
        )

        model = self._load_competency_model(target_role)
        questions = self._generate_questions(model, target_role, interview_type, num_questions)

        self.logger.info(f"面试出题完成，生成 {len(questions)} 道题")

        return self._success(
            data={"questions": questions, "total_count": len(questions),
                  "target_role": target_role, "interview_type": interview_type},
            message=f"为 [{target_role}] 岗位生成了 {len(questions)} 道{interview_type}面试题"
        )

    def _load_competency_model(self, role: str) -> Dict:
        """加载岗位能力模型"""
        role_map = {
            "管培生": "guanpeisheng",
            "AI产品实习生": "ai_product", "AI产品": "ai_product",
            "数据分析": "data_analyst", "数据分析师": "data_analyst",
            "前端开发": "frontend", "前端": "frontend",
            "后端开发": "backend", "后端": "backend",
            "市场营销": "marketing",
        }

        model_key = role_map.get(role)
        if not model_key:
            for key, value in role_map.items():
                if key in role or role in key:
                    model_key = value
                    break

        if not model_key:
            model_key = "guanpeisheng"
            self.logger.warning(f"未找到 [{role}] 的能力模型，使用默认管培生模型")

        filepath = os.path.join(COMPETENCY_DIR, f"{model_key}.json")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"能力模型文件不存在: {filepath}，使用内置题目")
            return self._get_builtin_model(role)

    def _generate_questions(self, model: Dict, role: str,
                            interview_type: str, num_questions: int) -> List[Dict]:
        """基于能力模型生成面试题"""
        all_questions = model.get("interview_questions", {})
        pool: List[Dict] = []

        if interview_type == "behavioral":
            pool = all_questions.get("behavioral", [])
        elif interview_type == "technical":
            pool = all_questions.get("technical", [])
        else:
            for qtype in ["behavioral", "technical", "comprehensive"]:
                pool.extend(all_questions.get(qtype, []))

        if not pool:
            pool = self._get_fallback_questions(role)

        selected = random.sample(pool, min(num_questions, len(pool)))

        questions: List[Dict] = []
        for idx, q in enumerate(selected, 1):
            questions.append({
                "id": idx,
                "question": q.get("q", ""),
                "type": q.get("type", interview_type),
                "difficulty": q.get("difficulty", "mid"),
                "dimension": q.get("dimension", "综合"),
                "reference_points": q.get("reference_points", self._generate_reference_points(q.get("q", ""))),
                "follow_up": q.get("follow_up", "")
            })

        return questions

    def _generate_reference_points(self, question: str) -> List[str]:
        """为没有预设参考要点的题目生成通用参考要点"""
        return [
            "使用STAR结构组织回答",
            "提供具体的时间、场景和数据",
            "突出个人贡献和成果",
            "体现岗位所需的核心能力"
        ]

    def _get_fallback_questions(self, role: str) -> List[Dict]:
        """内置通用面试题"""
        return [
            {"q": f"为什么你想申请{role}岗位？你对这个岗位有什么了解？",
             "dimension": "求职动机", "difficulty": "junior"},
            {"q": "请描述一个你在团队中遇到分歧的经历，你是如何解决的？",
             "dimension": "团队协作", "difficulty": "mid"},
            {"q": f"你认为做好{role}最重要的三个能力是什么？你具备哪些？",
             "dimension": "自我认知", "difficulty": "mid"},
            {"q": "描述一个你主动承担额外责任的经历，结果如何？",
             "dimension": "主动性", "difficulty": "mid"},
            {"q": "你最近学到的最有价值的一件事是什么？你是如何学到的？",
             "dimension": "学习能力", "difficulty": "junior"},
        ]

    def _get_builtin_model(self, role: str) -> Dict:
        """内置最小能力模型"""
        return {
            "role": role,
            "core_dimensions": {
                "comprehensive": {"weight": 1.0, "description": "综合能力"}
            },
            "interview_questions": {
                "behavioral": self._get_fallback_questions(role),
                "technical": [],
                "comprehensive": []
            }
        }
