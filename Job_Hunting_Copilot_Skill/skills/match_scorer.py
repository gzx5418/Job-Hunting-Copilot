"""
匹配评分 Skill (Match Scorer Skill)
AutoClaw Skill ID: match_scorer

职责：
  接收岗位列表（来自 job_scraper）和用户 Profile（user_resume.json），
  对每个岗位进行多维度匹配评分（0-100 分），
  输出排序后的 ScoredJobItem 列表，供 report_generator 使用。

触发场景（通常由 Pipeline 自动触发）：
  - 在 job_scraper 执行完毕后自动触发
  - 或当用户说"帮我筛选这些岗位"、"哪个岗位更适合我"

GLM 调度方式：
  GLM 将 jobs 列表和 user_profile 传入此 Skill 的 run() 方法。

架构说明：
  本 Skill 属于「语义密集型」任务，需要理解 JD 文本并评估匹配度。
  在 AutoClaw 框架的生产部署中，评分逻辑由 GLM 大模型完成语义级匹配；
  当前提供基于规则引擎的本地 Demo 实现，包含四维评分：
    - 技能契合度 (40%): 关键词覆盖率
    - 出勤时间匹配 (20%): 正则提取出勤要求并对比
    - 城市匹配 (20%): 字符串匹配
    - 学历背景匹配 (20%): 关键词检测
  当通过 AutoClaw 接入 GLM 后端时，_score_single_job() 将委托给 GLM 处理。
"""

import json
import os
import re
from typing import List, Dict, Any, Optional
from skills import AutoClawSkill


class MatchScorerSkill(AutoClawSkill):
    """
    匹配评分 Skill
    基于用户 Profile 对 JD 进行多维度评分（技能契合度/可用性/城市/背景）
    """

    SKILL_NAME = "match_scorer"
    SKILL_DESCRIPTION = "基于用户简历 Profile，对抓取的岗位列表进行 0-100 分的智能匹配评分并排序。"

    # 评分维度权重
    SCORING_WEIGHTS = {
        "skill_match": 0.40,      # 技能契合度（硬技能匹配）
        "availability_match": 0.20,  # 出勤时间/实习周期契合度
        "city_match": 0.20,       # 城市匹配度
        "background_match": 0.20  # 学历/背景匹配度
    }

    def run(self, jobs: List[Dict], user_profile: Optional[Dict] = None,
            user_profile_path: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        执行岗位匹配评分。

        :param jobs: job_scraper 输出的岗位列表
        :param user_profile: 用户 Profile 字典（直接传入）
        :param user_profile_path: 或从文件路径加载
        :return: 按匹配分排序的 scored_jobs 列表
        """
        self.validate_input({"jobs": jobs}, ["jobs"])

        # 加载用户 Profile
        if user_profile is None:
            user_profile = self._load_profile(user_profile_path)

        self.logger.info(f"开始匹配评分 | 用户：{user_profile.get('name', '未知')} | 岗位数：{len(jobs)}")
        self.logger.info(f"用户技能：{user_profile.get('skills', [])}")

        scored_jobs = []
        for job in jobs:
            scored_job = self._score_single_job(job, user_profile)
            scored_jobs.append(scored_job)

        # 按总分降序排序
        scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)

        # 统计摘要
        tier1 = [j for j in scored_jobs if j["match_score"] >= 75]
        tier2 = [j for j in scored_jobs if 50 <= j["match_score"] < 75]
        tier3 = [j for j in scored_jobs if j["match_score"] < 50]

        self.logger.info(f"评分完成 | Tier1:{len(tier1)} | Tier2:{len(tier2)} | Tier3:{len(tier3)}")

        return self._success(
            data={
                "scored_jobs": scored_jobs,
                "total": len(scored_jobs),
                "tier1_count": len(tier1),
                "tier2_count": len(tier2),
                "tier3_count": len(tier3)
            },
            message=f"共评分 {len(scored_jobs)} 个岗位，Tier1 强推荐 {len(tier1)} 个"
        )

    def _score_single_job(self, job: Dict, user: Dict) -> Dict:
        """对单个岗位进行多维度评分"""
        req_text = job.get("requirements", "") + " " + job.get("title", "")
        req_lower = req_text.lower()

        user_skills = [s.lower() for s in user.get("skills", [])]
        user_city = user.get("target_city", "")
        availability = user.get("availability", "")
        education = user.get("education", {})

        # ── 1. 技能契合度 (40分) ──
        skill_score = 0
        matched_skills = []
        for skill in user_skills:
            if skill in req_lower:
                matched_skills.append(skill)
                skill_score += (40 / max(len(user_skills), 1))
        skill_score = min(skill_score, 40)

        # ── 2. 出勤时间匹配 (20分) ──
        avail_score = 10  # 默认中等偏下（无法判断时保守给分）
        req_fulltime = bool(re.search(r'(每周\s*5\s*天|5天.周|一周五天|full[- ]?time|全职)', req_text, re.IGNORECASE))
        req_days = re.search(r'每周\s*(\d)\s*天|(\d)\s*天\s*[/／]\s*周', req_text)
        required_days = int(req_days.group(1) or req_days.group(2)) if req_days else (5 if req_fulltime else None)

        avail_days_match = re.search(r'每周\s*(\d)\s*天', availability)
        avail_days = int(avail_days_match.group(1)) if avail_days_match else None
        avail_months_match = re.search(r'(\d+)\s*个?月', availability)
        avail_months = int(avail_months_match.group(1)) if avail_months_match else None

        if required_days and avail_days:
            if avail_days >= required_days:
                avail_score = 20
            elif avail_days >= required_days - 1:
                avail_score = 15
            else:
                avail_score = 5
        elif not required_days:
            avail_score = 15

        req_months_match = re.search(r'(\d+)\s*个?月', req_text)
        if req_months_match and avail_months:
            req_months = int(req_months_match.group(1))
            if avail_months >= req_months:
                avail_score = min(avail_score + 5, 20)
            elif avail_months < req_months - 1:
                avail_score = min(avail_score, 10)

        # ── 3. 城市匹配 (20分) ──
        job_location = job.get("location", "")
        city_score = 20 if user_city in job_location else 5

        # ── 4. 学历/背景 (20分) ──
        bg_score = 15  # 默认中等匹配
        degree = education.get("degree", "")
        if "硕士" in req_text or "研究生" in req_text:
            bg_score = 20 if any(d in degree for d in ["硕士", "研究生", "研一", "研二"]) else 8
        if "本科" in req_text:
            bg_score = 20

        # ── 总分计算 ──
        total_score = int(skill_score + avail_score + city_score + bg_score)
        total_score = min(max(total_score, 0), 100)

        # ── 生成评估理由 ──
        reason = self._generate_reason(
            total_score, matched_skills, avail_score, city_score, job.get("company", "")
        )

        # ── 打上 Tier 标签 ──
        if total_score >= 75:
            tier = "Tier 1 ⭐ 强烈推荐"
        elif total_score >= 50:
            tier = "Tier 2 ✅ 推荐投递"
        else:
            tier = "Tier 3 ⚠️ 可尝试"

        scored = dict(job)
        scored["match_score"] = total_score
        scored["match_reason"] = reason
        scored["tier"] = tier
        scored["matched_skills"] = matched_skills
        return scored

    def _generate_reason(self, score: int, matched_skills: List[str],
                         avail_score: int, city_score: int, company: str) -> str:
        """根据评分生成自然语言评估建议"""
        reasons = []

        if matched_skills:
            reasons.append(f"技能匹配：{', '.join(matched_skills[:3])}")
        else:
            reasons.append("技能重叠度较低，建议针对性补充")

        if avail_score < 10:
            reasons.append("⚠️ 出勤时间可能冲突，请确认")
        if city_score < 10:
            reasons.append("⚠️ 工作城市与目标城市不符")

        if score >= 80:
            prefix = f"强烈推荐：{company} 高度匹配"
        elif score >= 65:
            prefix = f"推荐投递：基本匹配"
        elif score >= 50:
            prefix = "可以尝试：部分条件符合"
        else:
            prefix = "不建议：存在明显不匹配条件"

        return f"{prefix}。{' | '.join(reasons)}"

    def _load_profile(self, path: str = None) -> Dict:
        """加载用户 Profile"""
        if path is None:
            path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "assets", "user_resume.json"
            )
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"未找到 Profile 文件: {path}，使用默认值")
            return {"skills": ["Python", "Axure", "Prompt Engineering"], "target_city": "上海"}
