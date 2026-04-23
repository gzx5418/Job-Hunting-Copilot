# 学习成长智能体 · 「学术与职场」数字助手
### 基于 AutoClaw 框架 × GLM 大模型调度 | 赛题二参赛作品

---

## 🏆 项目概览

本项目是「赛题二：学习成长智能体」的完整实现，围绕**学生求职全链路**（简历 → 岗位聚合 → 智能匹配）构建了基于 **AutoClaw 框架**的端到端自动化智能体，解决两大核心痛点：

| 赛题案例 | 真实痛点 | 本项目解决方案 |
|:---|:---|:---|
| **案例 2**：校招简历生成 | 大四毕业生面对空白模板无从下手 | 3 个 Skill 串联，草稿→STAR打磨→Word简历一键生成 |
| **案例 3**：实习聚合器 | 实习信息散落多平台，手动筛选耗时 | Browser→GLM→Excel 跨应用闭环，自动生成对比表 |

---

## 🏗️ AutoClaw 框架架构

```
用户自然语言指令
       │
       ▼
┌─────────────────────────────────────┐
│      GLM 大模型 (意图识别 & 路由)       │
│   "帮我找上海AI产品实习" → Pipeline     │
└────────┬────────────────────────────┘
         │ 调度 (agent_config.json 配置驱动)
         ▼
┌─────────────────────────────────────┐
│    AutoClaw Agent (agent.py)         │
│    按 Pipeline 步骤顺序执行 Skill     │
└──┬────────┬────────────┬────────────┘
   │        │            │
[Skill 1] [Skill 2]  [Skill 3]
经历萃取  STAR 打磨   Word导出
   │         跨应用协作链路
   ▼        ▼             ▼
Browser → GLM 解析 → Excel/Word 文件
```

---

## 🛠️ 核心 Skill 封装（6 个独立技能单元）

| Skill ID | 职责 | 跨应用能力 |
|:---|:---|:---|
| `experience_extractor` | 从非结构化草稿中提取时间、角色、成就 | 文本 → 结构化数据 |
| `star_polisher` | 按 STAR 原则重构经历，针对 JD 关键词优化 | GLM 语义理解 |
| `resume_writer` | 填充简历模板，导出 Word 文件 | **→ Word (.docx)** |
| `job_scraper` | 驱动浏览器跨平台抓取，自动翻页 | **Browser → 结构化数据** |
| `match_scorer` | 多维度评分（技能/时间/城市/背景），Tier 分级 | GLM 推理 |
| `report_generator` | 写入 Excel，条件格式高亮，冻结行 | **→ Excel (.xlsx)** |

---

## 🔀 自动化 Pipeline（2 条闭环链路）

### Pipeline 1 — 个性化校招简历生成（案例 2）
```
用户草稿 → [ExperienceExtractor] → [StarPolisher] → [ResumeWriter] → 简历.docx
            提取结构化经历          STAR 重构润色      填模板导出
```

### Pipeline 2 — 实习职位自动聚合器（案例 3）
```
岗位关键词 → [JobScraper] → [MatchScorer] → [ReportGenerator] → 对比表.xlsx
              浏览器抓取     简历匹配评分      Excel 格式化写出
```

---

## 🔗 跨应用协作链路（核心亮点）

```
Step 1: Browser（AutoClaw WebDriver）
        → 自动翻页抓取 BOSS直聘、实习僧、牛客等平台

Step 2: GLM（大模型语义解析）
        → 理解 JD 文本，完成语义级技能匹配评分

Step 3: Microsoft Excel（.xlsx）
        → ReportGenerator 写入对比表，绿/黄/红条件色块

Step 4: Microsoft Word（.docx）
        → ResumeWriter 填充简历模板，导出至本地 output/
```

---

## 🚀 快速开始

### 1. 环境准备
```bash
pip install -r requirements.txt
```

### 2. 启动全流程演示（一键运行两大场景）
```bash
cd Job_Hunting_Copilot_Skill
python agent.py
```

### 3. 查看生成文件
```
output/
├── 【管培生】李四_定向简历.docx     ← 场景一输出
└── 上海_AI产品实习_实习申请对比表.xlsx  ← 场景二输出
```

---

## 📁 完整目录结构

```
Job_Hunting_Copilot_Skill/
│
├── agent.py                      # ⭐ AutoClaw 调度引擎（GLM Pipeline Dispatcher）
├── agent_config.json             # ⭐ 配置文件：Skill注册 + Pipeline定义 + 路由规则
├── SKILL.md                      # Skill 封装说明（赛题标准格式）
├── requirements.txt              # Python 依赖清单
│
├── skills/                       # ⭐ 独立 Skill 模块（每个文件 = 一个原子能力）
│   ├── __init__.py               # AutoClaw Skill 基类（标准 run() 接口）
│   ├── experience_extractor.py   # 经历萃取 Skill
│   ├── star_polisher.py          # 亮点打磨 Skill（STAR 原则）
│   ├── resume_writer.py          # 排版适配 Skill（→ Word 导出）
│   ├── web_job_scraper.py        # 数据抓取 Skill（Browser 跨平台）
│   ├── match_scorer.py           # 匹配评分 Skill（多维度 0-100 分）
│   └── report_generator.py       # 报告生成 Skill（→ Excel 导出）
│
├── assets/
│   ├── user_resume.json          # 用户画像（技能/意向城市/出勤时间）
│   └── resume_template.md        # 简历 Markdown 模板（STAR 格式）
│
├── references/
│   ├── resume_standards.md       # 简历打磨规范（STAR/动词表/量化公式）
│   └── scoring_criteria.md       # 岗位匹配评分准则（Tier 分级标准）
│
├── scripts/                      # 早期脚本（已被 skills/ 体系取代，保留参考）
│   ├── generate_resume.py
│   ├── match_jobs.py
│   ├── generate_comparison.py
│   ├── job_scraper.py
│   └── full_pipeline.py
│
└── output/                       # 自动生成的输出文件（.docx / .xlsx）
```

---

## 📦 依赖说明

| 依赖 | 用途 |
|:---|:---|
| `python-docx` | 生成 Word 格式简历文件 |
| `pandas` | DataFrame 操作与 Excel 初始写入 |
| `openpyxl` | Excel 条件格式、列宽、冻结行等精细化格式控制 |
| `AutoClaw WebDriver` | 真实部署时驱动浏览器进行跨平台岗位抓取 |
| `GLM-4-Plus` | 意图理解、STAR 内容重写、语义级评分（API 集成） |
