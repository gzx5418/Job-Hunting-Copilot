# 学习成长智能体 -- 「学术与职场」数字助手

**基于 AutoClaw 框架 x GLM-4-Plus | 路径B：原生 Skill 模式 | 赛题二参赛作品**

---

## 项目概览

本项目是「赛题二：学习成长智能体」的完整实现，围绕学生学习生活与职业发展构建了端到端自动化智能体。采用 **路径 B（原生 Skill 模式）**，将核心业务能力封装为 11 个独立的原子化 Skill，由 GLM 大模型调度完成闭环任务。

| 赛题场景 | 真实痛点 | 解决方案 |
|:---|:---|:---|
| **案例 2**：校招简历生成 | 面对空白模板无从下手 | JD 分析 + 经历萃取 + STAR 打磨 + Word 导出 |
| **案例 3**：实习聚合器 | 信息散落多平台 | Browser 抓取 + 智能匹配 + Excel 对比表 |
| **典型场景**：文献调研 | 论文搜索效率低 | 学术搜索 + 文献提炼 + Word 综述报告 |

---

## 技术架构

```
用户指令（一句话）
       |
       v
GLM-4-Plus（大脑：意图识别 & Pipeline 调度）
       |
       v
AutoClaw 框架（执行器：Pipeline 编排 & 数据流管理）
       |
       v
11 个原子化 Skill（按 5 条 Pipeline 编排执行）
       |
       v
输出文件（Word 简历 / Excel 对比表 / Word 文献综述）
```

---

## 11 个原子化 Skill

| Skill ID | 职责 | 跨应用能力 |
|:---|:---|:---|
| `ocr_extractor` | 证书照片 OCR 识别，提取证书经历 | 图像 -> 结构化数据 |
| `jd_analyzer` | 从 JD 文本提取硬技能、软素质、学历要求 | GLM 语义分析 |
| `experience_extractor` | 从非结构化草稿提取时间、角色、成就 | 文本 -> 结构化数据 |
| `star_polisher` | STAR 原则重构经历，结合 JD 关键词优化 | GLM 语义改写 |
| `resume_writer` | 填充简历模板，导出 Word 文件 | **-> Word (.docx)** |
| `job_scraper` | 驱动浏览器跨平台抓取，自动翻页 | **Browser -> 数据** |
| `match_scorer` | 四维评分（技能/出勤/城市/学历），Tier 分级 | GLM 语义匹配 |
| `report_generator` | 写入 Excel，条件格式高亮，冻结行 | **-> Excel (.xlsx)** |
| `academic_search` | 调用 Semantic Scholar API 搜索论文 | HTTP API -> 论文列表 |
| `paper_digest` | 论文摘要结构化提炼（方法/发现/结论） | GLM 语义提炼 |
| `literature_report` | 生成 Word 文献综述报告（表格+趋势+建议） | **-> Word (.docx)** |

---

## 5 条自动化 Pipeline

### Pipeline 1 -- 个性化简历生成（JD 定制）
```
草稿+JD -> [JDAnalyzer] -> [ExperienceExtractor] -> [STARPolisher] -> [ResumeWriter] -> 简历.docx
            提取岗位要求     提取结构化经历         JD定制打磨        Word导出
```

### Pipeline 2 -- 证书识别 + 简历生成
```
证书照片 -> [OCRExtractor] -> [JDAnalyzer] -> [STARPolisher] -> [ResumeWriter] -> 简历.docx
            OCR识别经历        提取岗位要求      打磨经历          Word导出
```

### Pipeline 3 -- 实习职位自动聚合（案例 3）
```
关键词+城市 -> [JobScraper] -> [MatchScorer] -> [ReportGenerator] -> 对比表.xlsx
               浏览器抓取       匹配评分         Excel格式化
```

### Pipeline 4 -- 全自动文献调研
```
研究主题 -> [AcademicSearch] -> [PaperDigest] -> [LiteratureReport] -> 综述报告.docx
            API搜索论文        结构化提炼        Word报告生成
```

### Pipeline 5 -- 完整求职全流程
```
一键触发 -> [简历生成Pipeline] -> [实习聚合Pipeline] -> 简历.docx + 对比表.xlsx
```

---

## 跨应用协作链路

```
Step 1: Browser（AutoClaw WebDriver）
        -> 自动翻页抓取 BOSS直聘、实习僧、牛客等平台
        -> OCR 识别证书照片

Step 2: GLM-4-Plus（大模型语义解析）
        -> JD Analyzer 解析岗位要求
        -> STAR Polisher 改写经历
        -> Match Scorer 语义评分
        -> Paper Digest 文献提炼

Step 3: Microsoft Excel（.xlsx）
        -> ReportGenerator 写入对比表，条件格式色块

Step 4: Microsoft Word（.docx）
        -> ResumeWriter 生成简历
        -> LiteratureReport 生成文献综述
```

---

## 快速开始

### 环境准备
```bash
pip install -r Job_Hunting_Copilot_Skill/requirements.txt
```

### 方式一：交互式演示（推荐）
```bash
cd Job_Hunting_Copilot_Skill
python cli.py
```

菜单选项：
```
[1] 生成简历      -- 输入经历草稿 + 目标岗位 + JD
[2] 搜索实习      -- 输入岗位关键词 + 城市
[3] 文献调研      -- 输入研究主题
[4] 证书识别      -- 输入证书照片路径
[5] 一站式全流程  -- 简历 + 岗位聚合
[6] 多岗位对比    -- 同时生成多个岗位的定制简历
```

### 方式二：全流程自动演示
```bash
cd Job_Hunting_Copilot_Skill
python agent.py
```

### 查看生成文件
```
output/
├── 【管培生】李四_定向简历.docx              <- 简历
├── 上海_AI产品实习_实习对比表.xlsx            <- 岗位对比表
└── 大语言模型在教育领域的应用_文献综述报告.docx  <- 文献综述
```

---

## 目录结构

```
Job_Hunting_Copilot_Skill/
├── SKILL.md                       # Skill 封装说明（赛题标准格式）
├── agent.py                       # AutoClaw 调度引擎（Pipeline 执行器）
├── agent_config.json              # Skill 注册表 + Pipeline 定义 + 路由规则
├── cli.py                         # 交互式演示入口
├── requirements.txt               # Python 依赖清单
├── generate_opensource_notice.py  # 开源组件说明文档生成脚本
│
├── skills/                        # 11 个独立 Skill 模块
│   ├── __init__.py                #   AutoClaw Skill 基类
│   ├── ocr_extractor.py           #   证书 OCR 提取
│   ├── jd_analyzer.py             #   JD 分析
│   ├── experience_extractor.py    #   经历萃取
│   ├── star_polisher.py           #   STAR 亮点打磨
│   ├── resume_writer.py           #   Word 简历导出
│   ├── web_job_scraper.py         #   跨平台岗位抓取
│   ├── match_scorer.py            #   匹配评分
│   ├── report_generator.py        #   Excel 对比表生成
│   ├── academic_search.py         #   学术论文搜索
│   ├── paper_digest.py            #   文献结构化提炼
│   └── literature_report.py       #   Word 文献综述生成
│
├── assets/
│   ├── user_resume.json           #   用户画像数据
│   └── resume_template.md         #   简历 Markdown 模板
│
├── references/
│   ├── resume_standards.md        #   STAR 打磨规范
│   └── scoring_criteria.md        #   岗位评分准则
│
└── output/                        #   自动生成的输出文件
```

---

## 依赖说明

| 依赖 | 用途 |
|:---|:---|
| `python-docx` | Word 文件生成（简历 + 文献综述） |
| `pandas` | DataFrame 操作与 Excel 初始写入 |
| `openpyxl` | Excel 条件格式、列宽、冻结行 |
| `AutoClaw WebDriver` | 浏览器自动化（真实部署时启用） |
| `GLM-4-Plus` | 意图理解、STAR 改写、语义评分（AutoClaw 框架集成） |
| `easyocr` (可选) | 证书照片 OCR 识别 |

---

## 设计亮点

- **Skill 原子化**：11 个 Skill 各自独立，单一职责，可自由组合
- **配置驱动**：新增 Skill 只需编辑 `agent_config.json`，无需修改引擎
- **GLM 委托机制**：语义密集型任务（STAR 改写、JD 匹配）标注 `glm_delegation`，由 GLM 处理
- **跨应用闭环**：Browser -> GLM -> Excel/Word，真正替代人工操作
- **优雅降级**：API 限流时自动降级为演示数据，python-docx 缺失时降级为 Markdown
