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
import json
import time
import random
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode, quote
from skills import AutoClawSkill


# ------------------------------------------------------------------
# 平台配置注册表
# ------------------------------------------------------------------
PLATFORM_REGISTRY = {
    "zhipin": {
        "name": "BOSS直聘",
        "search_url": "https://www.zhipin.com/web/geek/job?query={keyword}&city={city_code}",
        "city_codes": {"上海": "101020100", "北京": "101010100", "深圳": "101280600", "杭州": "101210100"},
        "selectors": {
            "job_list": ".job-card-wrapper",
            "title": ".job-name .name",
            "salary": ".salary",
            "company": ".company-info .name",
            "location": ".job-area",
            "tags": ".tag-list .tag-item",
            "description": ".job-desc"
        },
        "anti_crawl": "medium",
        "pagination": "scroll",
        "wait_selector": ".job-card-wrapper"
    },
    "shixiseng": {
        "name": "实习僧",
        "search_url": "https://www.shixiseng.com/interns?keyword={keyword}&city={city}",
        "city_codes": {"上海": "上海", "北京": "北京", "深圳": "深圳"},
        "selectors": {
            "job_list": ".intern-wrap",
            "title": ".intern-title",
            "salary": ".day-work-pay",
            "company": ".company-name",
            "location": ".city",
            "tags": ".intern-tags .tag",
            "description": ".intern-desc"
        },
        "anti_crawl": "low",
        "pagination": "click_next",
        "wait_selector": ".intern-wrap"
    },
    "nowcoder": {
        "name": "牛客",
        "search_url": "https://www.nowcoder.com/jobs/internship?keyword={keyword}&city={city}",
        "city_codes": {"上海": "上海", "北京": "北京"},
        "selectors": {
            "job_list": ".job-item",
            "title": ".job-name",
            "salary": ".job-salary",
            "company": ".company-name",
            "location": ".job-city",
            "tags": ".job-tags .tag",
            "description": ".job-desc"
        },
        "anti_crawl": "low",
        "pagination": "click_next",
        "wait_selector": ".job-item"
    },
    "liepin": {
        "name": "猎聘",
        "search_url": "https://www.liepin.com/zhaopin/?key={keyword}&city={city_code}",
        "city_codes": {"上海": "040", "北京": "010"},
        "selectors": {
            "job_list": ".job-list-item",
            "title": ".job-title",
            "salary": ".job-salary",
            "company": ".company-name",
            "location": ".job-area",
            "tags": ".job-tags .tag",
            "description": ".job-desc"
        },
        "anti_crawl": "high",
        "pagination": "click_next",
        "wait_selector": ".job-list-item"
    },
    "lagou": {
        "name": "拉勾",
        "search_url": "https://www.lagou.com/wn/zhaopin?kd={keyword}&city={city}",
        "city_codes": {},
        "selectors": {
            "job_list": ".position-list-item",
            "title": ".position-name",
            "salary": ".salary",
            "company": ".company-name",
            "location": ".position-city",
            "tags": ".position-tags .tag",
            "description": ".position-desc"
        },
        "anti_crawl": "high",
        "pagination": "click_next",
        "wait_selector": ".position-list-item"
    }
}


class JobScraperSkill(AutoClawSkill):
    """
    数据抓取 Skill
    跨平台并发抓取实习/校招岗位列表，返回标准化 JobItem 列表
    默认通过 AutoClaw WebDriver 执行真实浏览器抓取
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
        :return: 标准化的 jobs 列表 + browser_tasks（如需浏览器操作）
        """
        self.validate_input({"keyword": keyword}, ["keyword"])

        platforms = platforms or ["zhipin", "shixiseng", "nowcoder"]
        all_jobs: List[Dict] = []
        browser_tasks: List[Dict] = []
        pending_platforms: List[str] = []

        self.logger.info(f"开始跨平台抓取 | 关键词: {keyword} | 城市: {city} | 平台: {platforms}")

        for platform_key in platforms:
            platform_cfg = PLATFORM_REGISTRY.get(platform_key)
            if not platform_cfg:
                self.logger.warning(f"未知平台: {platform_key}，跳过")
                continue

            platform_name = platform_cfg["name"]

            if web_contents and platform_key in web_contents:
                # 模式A：AutoClaw WebDriver 已完成抓取，直接解析真实内容
                raw_content = web_contents[platform_key]
                self.logger.info(f"  → [{platform_name}] 解析 WebDriver 返回的真实数据...")
                jobs = self._parse_content(raw_content, platform_key, keyword, city)
                all_jobs.extend(jobs)
                self.logger.info(f"  → [{platform_name}] 解析到 {len(jobs)} 条岗位")
            else:
                # 模式B：生成浏览器抓取任务，等待 AutoClaw 执行
                task = self._build_browser_task(platform_key, platform_cfg, keyword, city, max_pages)
                browser_tasks.append(task)
                pending_platforms.append(platform_name)
                self.logger.info(f"  → [{platform_name}] 已生成浏览器抓取任务，等待 WebDriver 执行")

            # 防反爬延迟
            time.sleep(random.uniform(0.5, 1.5))

        # 如果有待执行的浏览器任务，返回任务列表让 AutoClaw 调度
        if browser_tasks and not all_jobs:
            return self._success(
                data={
                    "status": "pending_browser",
                    "browser_tasks": browser_tasks,
                    "message": f"已生成 {len(browser_tasks)} 个浏览器抓取任务，请 WebDriver 执行后重新调用"
                },
                message=f"已生成 {len(browser_tasks)} 个平台 ({', '.join(pending_platforms)}) 的浏览器抓取任务"
            )

        # 如果有部分任务待执行但已有部分结果
        if browser_tasks:
            return self._success(
                data={
                    "jobs": self._deduplicate(all_jobs),
                    "total_count": len(all_jobs),
                    "keyword": keyword,
                    "city": city,
                    "pending_browser_tasks": browser_tasks
                },
                message=f"已获取 {len(all_jobs)} 条岗位，还有 {len(browser_tasks)} 个平台待浏览器抓取"
            )

        # 全部解析完成
        all_jobs = self._deduplicate(all_jobs)
        self.logger.info(f"抓取完成，共获取 {len(all_jobs)} 条去重岗位")

        return self._success(
            data={"jobs": all_jobs, "total_count": len(all_jobs),
                  "keyword": keyword, "city": city},
            message=f"跨 {len(platforms)} 个平台抓取完成，共获得 {len(all_jobs)} 条岗位"
        )

    def _build_browser_task(self, platform_key: str, platform_cfg: Dict,
                             keyword: str, city: str, max_pages: int) -> Dict:
        """
        生成 AutoClaw WebDriver 浏览器抓取任务指令。
        AutoClaw 的 autoglm-browser-agent 会根据这些指令驱动浏览器。
        """
        city_code = platform_cfg.get("city_codes", {}).get(city, city)
        search_url = platform_cfg.get("search_url", "").format(
            keyword=quote(keyword), city=quote(city), city_code=city_code
        )

        selectors = platform_cfg.get("selectors", {})
        wait_selector = platform_cfg.get("wait_selector", "")

        task = {
            "platform": platform_key,
            "platform_name": platform_cfg["name"],
            "action": "scrape_jobs",
            "url": search_url,
            "max_pages": max_pages,
            "pagination_type": platform_cfg.get("pagination", "click_next"),
            "wait_for": {
                "selector": wait_selector,
                "timeout_ms": 10000
            },
            "extract_config": {
                "list_selector": selectors.get("job_list", ""),
                "fields": {
                    "title": selectors.get("title", ""),
                    "salary": selectors.get("salary", ""),
                    "company": selectors.get("company", ""),
                    "location": selectors.get("location", ""),
                    "tags": selectors.get("tags", ""),
                    "description": selectors.get("description", "")
                }
            },
            "anti_crawl": {
                "level": platform_cfg.get("anti_crawl", "low"),
                "random_delay_ms": [800, 2500],
                "scroll_before_extract": True,
                "simulate_human": True
            }
        }

        self.logger.info(f"    [浏览器任务] {platform_cfg['name']} → {search_url}")
        return task

    def _parse_content(self, content: str, platform: str,
                       keyword: str, city: str) -> List[Dict]:
        """解析 AutoClaw WebDriver 返回的网页原始内容（真实数据）"""
        platform_cfg = PLATFORM_REGISTRY.get(platform, {})
        platform_name = platform_cfg.get("name", platform)

        # 尝试解析 JSON 格式（WebDriver 结构化提取结果）
        jobs = self._try_parse_structured(content, platform_name, keyword, city)
        if jobs:
            return jobs

        # 回退到文本块解析
        jobs = self._try_parse_text_blocks(content, platform_name, keyword, city)
        if jobs:
            return jobs

        # 两种方式都未能解析，记录警告并返回空列表
        self.logger.warning(
            f"  [{platform_name}] 未能从 WebDriver 内容中提取岗位数据。"
            f"内容长度: {len(content)} 字符，前200字: {content[:200]}"
        )
        return []

    def _try_parse_structured(self, content: str, platform_name: str,
                              keyword: str, city: str) -> List[Dict]:
        """尝试解析 WebDriver 返回的结构化 JSON 数据"""
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return []

        # WebDriver 可能返回列表形式的岗位数据
        items = data if isinstance(data, list) else data.get("jobs", data.get("items", data.get("results", [])))
        if not isinstance(items, list):
            return []

        jobs: List[Dict] = []
        for item in items[:30]:
            if not isinstance(item, dict):
                continue
            title = item.get("title") or item.get("name") or ""
            if not title:
                continue

            salary = item.get("salary") or item.get("pay") or "面议"
            location = item.get("location") or item.get("city") or item.get("area") or city
            company = item.get("company") or item.get("company_name") or "未知"
            tags = item.get("tags") or item.get("skills") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]

            jobs.append({
                "source": platform_name,
                "title": title,
                "company": company,
                "salary": str(salary),
                "location": str(location),
                "requirements": ", ".join(tags) if tags else "",
                "url": item.get("url", item.get("link", "")),
                "scraped_by": "AutoClaw_WebDriver"
            })

        return jobs

    def _try_parse_text_blocks(self, content: str, platform_name: str,
                                keyword: str, city: str) -> List[Dict]:
        """从文本块中解析岗位信息（WebDriver 返回纯文本时的降级方案）"""
        jobs: List[Dict] = []
        # platform_name 是中文名（如"BOSS直聘"），需要反查英文键
        platform_key = next((k for k, v in PLATFORM_REGISTRY.items() if v.get("name") == platform_name), None)
        platform_cfg = PLATFORM_REGISTRY.get(platform_key, {}) if platform_key else {}

        # 按段落分割，寻找岗位卡片
        blocks = [b.strip() for b in content.split('\n\n') if b.strip()]

        for block in blocks[:30]:
            # 至少包含关键词或城市名才可能是岗位信息
            has_keyword = keyword.lower() in block.lower()
            has_city = city in block
            has_salary = bool(re.search(r'\d+[Kk\-/天]', block))
            has_company = bool(re.search(r'(有限公司|科技|集团|公司)', block))

            if not (has_keyword or has_city or has_salary or has_company):
                continue

            title = self._extract_field_from_block(block, ['岗位', '职位', '招聘', '实习生', '工程师', '经理'])
            company = self._extract_field_from_block(block, ['公司', '企业', '有限公司', '科技'])
            salary = self._extract_salary(block)
            location = self._extract_location(block, city)

            if title and title != "未知":
                jobs.append({
                    "source": platform_name,
                    "title": title,
                    "company": company if company != "未知" else "未知",
                    "salary": salary,
                    "location": location,
                    "requirements": block[:500],
                    "url": platform_cfg.get("search_url", ""),
                    "scraped_by": "AutoClaw_WebDriver"
                })

        return jobs

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
        patterns = [
            r'\d{1,3}[Kk]-\d{1,3}[Kk]',
            r'\d{1,3}-\d{1,3}K',
            r'\d{3,5}-\d{3,5}元',
            r'\d{2,3}-\d{2,3}/天',
            r'\d{1,5}-\d{1,5}·\d{1,2}薪',
            r'面议'
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group()
        return "面议"

    def _extract_location(self, text: str, city: str) -> str:
        """提取工作地点"""
        pattern = rf'{city}[··\s\-]?[\u4e00-\u9fa5]+'
        m = re.search(pattern, text)
        return m.group() if m else city

    def _deduplicate(self, jobs: List[Dict]) -> List[Dict]:
        """基于公司+岗位名去重"""
        seen: set = set()
        unique: List[Dict] = []
        for job in jobs:
            key = f"{job.get('company', '')}_{job.get('title', '')}"
            if key not in seen:
                seen.add(key)
                unique.append(job)
        return unique
