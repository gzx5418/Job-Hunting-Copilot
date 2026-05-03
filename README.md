# 求职智能体 -- 基于 AutoClaw（小龙虾）的学术与职场 Skill 插件包

**AutoClaw 路径B：原生 Skill 模式 | GLM-4-Plus | 14 Skills × 7 Pipelines**

---

## 项目概览

本项目是面向 AutoClaw（小龙虾）框架开发的 **Skill 插件包**，严格遵循路径B（原生 Skill 模式）规范。安装后用户可在 AutoClaw 中直接通过自然语言调用求职与学术相关能力：14 个原子化 Skill 按需组合为 7 条自动化 Pipeline，覆盖简历生成、岗位聚合、文献调研、模拟面试等场景，实现 Browser → GLM → Excel/Word 的跨应用闭环。

| 赛题场景 | 真实痛点 | 解决方案 |
|:---|:---|:---|
| **案例 2**：校招简历生成 | 面对空白模板无从下手 | JD 分析 + 经历萃取 + STAR 打磨 + Word 导出 |
| **案例 3**：实习聚合器 | 信息散落多平台 | Browser 抓取 + 智能匹配 + Excel 对比表 |
| **典型场景**：文献调研 | 论文搜索效率低 | 学术搜索 + 文献提炼 + Word 综述报告 |
| **典型场景**：模拟面试 | 缺乏面试练习环境 | 岗位能力建模 + 结构化出题 + 四维评分 + 练习报告 |

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
14 个原子化 Skill（按 7 条 Pipeline 编排执行）
       |
       v
输出文件（Word 简历 / Excel 对比表 / Word 文献综述 / Word 面试报告）
```

---

## 14 个原子化 Skill

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
| `academic_search` | 通过 AutoClaw MCP_WebReader 搜索学术论文 | Web 搜索 -> 论文列表 |
| `paper_digest` | 论文摘要结构化提炼（方法/发现/结论） | GLM 语义提炼 |
| `literature_report` | 生成 Word 文献综述报告（表格+趋势+建议） | **-> Word (.docx)** |
| `interview_questioner` | 基于岗位能力模型生成结构化面试题（技术/行为/综合） | GLM 结构化出题 |
| `interview_scorer` | 四维评分体系（完整度/条理性/STAR/关键词）评估面试回答 | GLM 多维评估 |
| `interview_report` | 生成 Word 面试练习报告，含维度分析和改进建议 | **-> Word (.docx)** |

---

## 7 条自动化 Pipeline

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

### Pipeline 6 -- 模拟面试练习
```
岗位类型 -> [InterviewQuestioner] -> [InterviewScorer] -> [InterviewReport] -> 面试报告.docx
            能力模型出题           四维评分评估        维度分析报告
```

### Pipeline 7 -- 简历 + 面试联动
```
一键触发 -> [简历生成Pipeline] -> [模拟面试Pipeline] -> 简历.docx + 面试报告.docx
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
        -> Interview Questioner 结构化出题
        -> Interview Scorer 多维评分

Step 3: Microsoft Excel（.xlsx）
        -> ReportGenerator 写入对比表，条件格式色块

Step 4: Microsoft Word（.docx）
        -> ResumeWriter 生成简历
        -> LiteratureReport 生成文献综述
        -> InterviewReport 生成面试练习报告
```

---

## 模拟面试模块

### 功能概述

模拟面试模块提供从面试出题到评估反馈的完整练习闭环，帮助用户在真实面试前进行针对性训练。

### 核心能力

- **面试出题**：基于岗位能力模型，自动生成结构化面试题，覆盖技术题、行为题和综合题三类
- **面试评估**：采用四维评分体系（完整度/条理性/STAR/关键词），对用户回答进行多角度量化评估
- **面试报告**：生成 Word 格式的练习报告，包含各维度得分分析、薄弱项识别和改进建议

### 支持 6 个岗位能力模型

| 能力模型 | 文件 | 适用岗位 |
|:---|:---|:---|
| 管培生 | `guanpeisheng.json` | 管理培训生、综合管理岗 |
| AI 产品 | `ai_product.json` | AI 产品经理、产品实习生 |
| 数据分析 | `data_analyst.json` | 数据分析师、商业分析岗 |
| 前端开发 | `frontend.json` | 前端工程师、Web 开发岗 |
| 后端开发 | `backend.json` | 后端工程师、服务端开发岗 |
| 市场营销 | `marketing.json` | 市场营销、品牌运营岗 |

---

## Prompt 模板外置

所有 GLM 调用的系统提示词均以 Markdown 文件形式外置于 `prompts/` 目录，便于：

- **独立维护**：无需修改 Python 代码即可调整提示词策略
- **版本对比**：提示词变更可纳入 Git 版本管理
- **快速迭代**：针对不同场景可快速切换或 A/B 测试提示词

当前外置的 Prompt 模板：

| 模板文件 | 用途 |
|:---|:---|
| `jd_analysis_system.md` | JD 岗位分析系统提示词 |
| `experience_extract_system.md` | 经历萃取系统提示词 |
| `star_polish_system.md` | STAR 打磨系统提示词 |
| `star_polish_user.md` | STAR 打磨用户提示词模板 |
| `match_scoring_system.md` | 岗位匹配评分提示词 |
| `paper_digest_system.md` | 文献提炼系统提示词 |
| `interview_question_system.md` | 面试出题系统提示词 |
| `interview_score_system.md` | 面试评分系统提示词 |

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
[7] 模拟面试      -- 选择岗位类型，生成面试题并评估
[8] 简历+面试    -- 生成简历后自动进入面试练习
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
├── 大语言模型在教育领域的应用_文献综述报告.docx  <- 文献综述
└── 面试练习报告_管培生.docx                   <- 面试练习报告
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
├── skills/                        # 14 个独立 Skill 模块
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
│   ├── literature_report.py       #   Word 文献综述生成
│   ├── interview_questioner.py    #   面试出题（基于岗位能力模型）
│   ├── interview_scorer.py        #   面试评分（四维评分体系）
│   └── interview_report.py        #   Word 面试练习报告生成
│
├── prompts/                       # Prompt 模板外置（Markdown）
│   ├── prompt_loader.py           #   Prompt 加载器
│   ├── jd_analysis_system.md      #   JD 分析系统提示词
│   ├── experience_extract_system.md #  经历萃取系统提示词
│   ├── star_polish_system.md      #   STAR 打磨系统提示词
│   ├── star_polish_user.md        #   STAR 打磨用户提示词
│   ├── match_scoring_system.md    #   匹配评分系统提示词
│   ├── paper_digest_system.md     #   文献提炼系统提示词
│   ├── interview_question_system.md #  面试出题系统提示词
│   └── interview_score_system.md  #   面试评分系统提示词
│
├── assets/
│   ├── user_resume.json           #   用户画像数据
│   └── resume_template.md         #   简历 Markdown 模板
│
├── references/
│   ├── resume_standards.md        #   STAR 打磨规范
│   ├── scoring_criteria.md        #   岗位评分准则
│   ├── interview_scoring_criteria.md # 面试评分准则
│   └── competency_models/         #   岗位能力模型（JSON）
│       ├── guanpeisheng.json      #     管培生
│       ├── ai_product.json        #     AI 产品
│       ├── data_analyst.json      #     数据分析
│       ├── frontend.json          #     前端开发
│       ├── backend.json           #     后端开发
│       └── marketing.json         #     市场营销
│
└── output/                        #   自动生成的输出文件
```

---

## 依赖说明

| 依赖 | 用途 |
|:---|:---|
| `python-docx` | Word 文件生成（简历 + 文献综述 + 面试报告） |
| `pandas` | DataFrame 操作与 Excel 初始写入 |
| `openpyxl` | Excel 条件格式、列宽、冻结行 |
| `AutoClaw WebDriver` | 浏览器自动化（真实部署时启用） |
| `GLM-4-Plus` | 意图理解、STAR 改写、语义评分、面试出题与评估（AutoClaw 框架集成） |
| `AutoClaw GLM-4V` | 证书照片视觉识别（替代本地 OCR 引擎） |

---

## 设计亮点

- **Skill 原子化**：14 个 Skill 各自独立，单一职责，可自由组合
- **配置驱动**：新增 Skill 只需编辑 `agent_config.json`，无需修改引擎
- **Prompt 模板外置**：所有 GLM 提示词独立为 Markdown 文件，支持版本管理和快速迭代
- **GLM 委托机制**：语义密集型任务（STAR 改写、JD 匹配、面试出题）标注 `glm_delegation`，由 GLM 处理
- **岗位能力建模**：6 个预置能力模型，驱动面试出题和评分，确保面试练习的岗位针对性
- **跨应用闭环**：Browser -> GLM -> Excel/Word，真正替代人工操作
- **优雅降级**：python-docx 缺失时自动降级为 Markdown 输出；pending 状态支持异步工具协作
