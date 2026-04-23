"""
数据抓取 Skill (Web Job Scraper Skill)
AutoClaw Skill ID: job_scraper

职责：
  驱动 AutoClaw WebDriver（或 MCP WebReader 工具），
  自动翻页抓取特定岗位的薪资、地点、岗位要求等信息，
  支持 BOSS直聘、实习僧、牛客、猎聘、拉勾等主流平台。

跨应用能力：
  Browser → GLM (解析) → 标准化 JobItem 列表

触发场景：
  - "帮我找上海的 AI 产品实习"
  - "抓取 BOSS 和实习僧上的数据分析实习"
  - "搜索北京的管培生岗位"

GLM 调度方式：
  GLM 从用户指令中提取 keyword、city 后，
  调度此 Skill 执行抓取，并将结果传递给 match_scorer。
"""

import re
import time
import random
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode
from skills import AutoClawSkill


# ------------------------------------------------------------------
# 平台配置注册表
# ------------------------------------------------------------------
PLATFORM_REGISTRY = {
    "zhipin": {
        "name": "BOSS直聘",
        "search_url": "https://www.zhipin.com/web/geek/job?query={keyword}&city={city_code}",
        "city_codes": {"上海": "101020100", "北京": "101010100", "深圳": "101280600", "杭州": "101210100"},
        "selectors": {"job_list": ".job-card-wrapper", "title": ".job-name", "salary": ".salary", "company": ".company-name"},
        "anti_crawl": "medium",
        "pagination": "scroll"
    },
    "shixiseng": {
        "name": "实习僧",
        "search_url": "https://www.shixiseng.com/interns?keyword={keyword}&city={city}",
        "city_codes": {"上海": "上海", "北京": "北京", "深圳": "深圳"},
        "selectors": {"job_list": ".intern_item", "title": ".name", "salary": ".day_work_pay", "company": ".company_name"},
        "anti_crawl": "low",
        "pagination": "click_next"
    },
    "nowcoder": {
        "name": "牛客",
        "search_url": "https://www.nowcoder.com/jobs/internship?keyword={keyword}&city={city}",
        "city_codes": {"上海": "上海", "北京": "北京"},
        "selectors": {"job_list": ".job-item", "title": ".job-name", "salary": ".job-salary", "company": ".company-name"},
        "anti_crawl": "low",
        "pagination": "click_next"
    },
    "liepin": {
        "name": "猎聘",
        "search_url": "https://www.liepin.com/zhaopin/?key={keyword}&city={city_code}",
        "city_codes": {"上海": "040", "北京": "010"},
        "anti_crawl": "high",
        "pagination": "click_next"
    },
    "lagou": {
        "name": "拉勾",
        "search_url": "https://www.lagou.com/wn/zhaopin?kd={keyword}&city={city}",
        "anti_crawl": "high",
        "pagination": "click_next"
    }
}


class JobScraperSkill(AutoClawSkill):
    """
    数据抓取 Skill
    跨平台并发抓取实习/校招岗位列表，返回标准化 JobItem 列表
    """

    SKILL_NAME = "job_scraper"
    SKILL_DESCRIPTION = "驱动浏览器跨平台抓取岗位信息，支持多平台并发，自动翻页。"

    def run(self, keyword: str, city: str = "上海",
            platforms: List[str] = None, max_pages: int = 2,
            web_contents: Dict[str, str] = None, **kwargs) -> Dict[str, Any]:
        """
        执行岗位抓取。

        :param keyword: 岗位关键词（如 "AI 产品实习"）
        :param city: 目标城市（如 "上海"）
        :param platforms: 指定平台列表，默认 ["zhipin", "shixiseng", "nowcoder"]
        :param max_pages: 每个平台最大抓取页数
        :param web_contents: 可选，已由 AutoClaw WebDriver 抓取的原始网页内容
        :return: 标准化的 jobs 列表
        """
        self.validate_input({"keyword": keyword}, ["keyword"])

        platforms = platforms or ["zhipin", "shixiseng", "nowcoder"]
        all_jobs = []

        self.logger.info(f"开始跨平台抓取 | 关键词: {keyword} | 城市: {city} | 平台: {platforms}")

        for platform_key in platforms:
            platform_cfg = PLATFORM_REGISTRY.get(platform_key)
            if not platform_cfg:
                self.logger.warning(f"未知平台: {platform_key}，跳过")
                continue

            platform_name = platform_cfg["name"]
            self.logger.info(f"  → [{platform_name}] 开始抓取，最多 {max_pages} 页...")

            if web_contents and platform_key in web_contents:
                # 模式A：AutoClaw WebDriver 已完成抓取，直接解析内容
                raw_content = web_contents[platform_key]
                jobs = self._parse_content(raw_content, platform_key, keyword, city)
            else:
                # 模式B：生成抓取任务指令（在无 WebDriver 环境下的降级方案）
                jobs = self._generate_scrape_task(platform_key, platform_cfg, keyword, city, max_pages)

            all_jobs.extend(jobs)
            self.logger.info(f"  → [{platform_name}] 获取 {len(jobs)} 条岗位")

            # 防反爬延迟（模拟真实浏览行为）
            time.sleep(random.uniform(1.0, 2.5))

        # 去重（同一岗位可能在多平台出现）
        all_jobs = self._deduplicate(all_jobs)

        self.logger.info(f"抓取完成，共获取 {len(all_jobs)} 条去重岗位")

        return self._success(
            data={"jobs": all_jobs, "total_count": len(all_jobs),
                  "keyword": keyword, "city": city},
            message=f"跨 {len(platforms)} 个平台抓取完成，共获得 {len(all_jobs)} 条岗位"
        )

    def _parse_content(self, content: str, platform: str,
                       keyword: str, city: str) -> List[Dict]:
        """解析 AutoClaw WebDriver 返回的网页原始内容"""
        platform_cfg = PLATFORM_REGISTRY.get(platform, {})
        platform_name = platform_cfg.get("name", platform)

        jobs = []
        # 按段落分割，寻找岗位卡片
        blocks = [b.strip() for b in content.split('\n\n') if b.strip()]

        for block in blocks[:20]:  # 限制处理数量
            if keyword in block or city in block:
                job = {
                    "source": platform_name,
                    "title": self._extract_field_from_block(block, ['岗位', '职位', '招聘']),
                    "company": self._extract_field_from_block(block, ['公司', '企业']),
                    "salary": self._extract_salary(block),
                    "location": self._extract_location(block, city),
                    "requirements": block[:500],
                    "url": platform_cfg.get("search_url", "").format(keyword=keyword, city=city),
                    "scraped_by": "AutoClaw_WebDriver"
                }
                if job["title"] and job["title"] != "未知":
                    jobs.append(job)

        # 如果解析失败，返回模拟数据（演示用）
        if not jobs:
            self.logger.warning(f"  [{platform_name}] 未能解析真实数据，返回演示数据（demo_mode=True）")
            jobs = self._get_demo_data(platform_name, keyword, city)
            for job in jobs:
                job["demo_mode"] = True

        return jobs

    def _generate_scrape_task(self, platform_key: str, platform_cfg: Dict,
                               keyword: str, city: str, max_pages: int) -> List[Dict]:
        """
        当 AutoClaw WebDriver 未就绪时，生成抓取任务描述，
        同时返回模拟数据供演示使用。
        """
        city_code = platform_cfg.get("city_codes", {}).get(city, city)
        search_url = platform_cfg.get("search_url", "").format(
            keyword=keyword, city=city, city_code=city_code
        )

        self.logger.info(f"    [任务已生成] {platform_cfg['name']} - {search_url}")
        self.logger.info(f"    → 当前返回演示数据，部署 AutoClaw WebDriver 后将执行真实抓取")

        demo_data = self._get_demo_data(platform_cfg["name"], keyword, city)
        for job in demo_data:
            job["demo_mode"] = True
        return demo_data

    def _get_demo_data(self, platform_name: str, keyword: str, city: str) -> List[Dict]:
        """演示用模拟数据（真实部署时由 WebDriver 替代）"""
        demos = [
            {
                "source": platform_name,
                "company": "字节跳动",
                "title": f"{keyword} - 豆包方向",
                "salary": "200-300/天",
                "location": f"{city}·杨浦区",
                "requirements": f"需了解 LLM 原理，熟练使用 Axure，有 Prompt 调优经验优先。每周至少 4 天，实习 3 个月以上。",
                "url": "https://job.toutiao.com/demo",
                "scraped_by": "demo_mode"
            },
            {
                "source": platform_name,
                "company": "某 AI 独角兽",
                "title": f"{keyword} - 商业化方向",
                "salary": "250-350/天",
                "location": f"{city}·嘉定区",
                "requirements": "需商科/管理类背景，懂基础 SQL，善于沟通与竞品分析。重点看重 B 端 SaaS 经验。",
                "url": "https://example.com/demo",
                "scraped_by": "demo_mode"
            }
        ]
        return demos

    def _extract_field_from_block(self, block: str, keywords: List[str]) -> str:
        """从文本块中提取字段"""
        lines = block.split('\n')
        for line in lines:
            for kw in keywords:
                if kw in line:
                    return line.replace(kw, '').strip(':： ')
        return "未知"

    def _extract_salary(self, text: str) -> str:
        """提取薪资"""
        patterns = [r'\d{1,3}[Kk]-\d{1,3}[Kk]', r'\d{1,3}-\d{1,3}K', r'\d{3,5}-\d{3,5}元', r'\d{2,3}-\d{2,3}/天', r'面议']
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group()
        return "面议"

    def _extract_location(self, text: str, city: str) -> str:
        """提取工作地点"""
        pattern = rf'{city}[··\s]?[\u4e00-\u9fa5]+'
        m = re.search(pattern, text)
        return m.group() if m else city

    def _deduplicate(self, jobs: List[Dict]) -> List[Dict]:
        """基于公司+岗位名去重"""
        seen = set()
        unique = []
        for job in jobs:
            key = f"{job.get('company', '')}_{job.get('title', '')}"
            if key not in seen:
                seen.add(key)
                unique.append(job)
        return unique
