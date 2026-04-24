# 求职智能体 -- 「学术与职场」数字助手

**技能名称**：求职智能体

## 技能职责

本智能体专为学生学习生活与职业发展设计，基于 **AutoClaw 框架 + GLM-4-Plus** 构建。采用**路径 B（原生 Skill 模式）**，将核心业务能力封装为独立的原子化 Skill，由 GLM 大模型调度完成闭环任务。

核心能力聚焦于「个性化校招简历生成」「行业实习职位自动聚合」与「模拟面试练习」，旨在解决学生在求职初期简历"无从下手"、实习信息"碎片化"以及面试准备"缺乏反馈"的痛点。

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
原子化 Skill 库（14 个独立 Skill，按 Pipeline 编排执行）
     |
     v
输出文件（Word 简历 / Excel 对比表 / 面试练习报告）
```

**关键设计原则：**
- **Skill 原子化**：每个 Skill 封装单一职责的原子能力，独立可测
- **Pipeline 编排**：通过 `agent_config.json` 定义多步骤闭环流程，Skill 间数据流自动传递
- **GLM 调度**：语义密集型任务（STAR 改写、JD 匹配、面试评估）由 GLM 完成语义理解；结构化任务（文件生成、数据格式化）由 Skill 本地处理
- **跨应用协作**：Browser（抓取）-> GLM（分析）-> Excel/Word（输出）
- **Prompt 模板化**：所有 LLM 交互提示词通过 `prompts/` 目录统一管理，支持热更新与版本控制

---

## 核心 Skill 封装（14 个原子化 Skill）

### 1. JD 分析 Skill (JD Analyzer)
- **输入**：目标岗位的 JD 文本
- **动作**：提取硬技能要求、软素质要求、学历要求、出勤要求、核心关键词
- **输出**：`jd_keywords`（供下游 Skill 消费）、`jd_summary`（JD 摘要）

### 2. 经历萃取 Skill (Experience Extraction)
- **输入**：凌乱的校园经历草稿、社团经历记录、非结构化文本、证书描述
- **动作**：识别时间链路、组织机构、核心角色，将碎片化信息结构化为标准 ExperienceItem 列表
- **能力**：支持识别非职场话术（如"在社团打杂"）并转化为标准岗位职责

### 3. 亮点打磨 Skill (STAR Polishing)
- **核心标准**：严格遵守 **STAR 原则**（Situation 场景, Task 任务, Action 行动, Result 结果）
- **JD 定制**：结合 JD 分析输出的关键词，针对性打磨经历描述
- **优化逻辑**：
    - 针对目标岗位能力模型，自动提取领导力、协调能力、学习力关键词
    - Impact 化：将描述转化为数据支持的结果
- **GLM 委托**：STAR 改写属语义密集型任务，生产环境由 GLM 完成语义级重构

### 4. 排版适配 Skill (Resume Writer)
- **输入**：STAR 打磨后的 Markdown 内容 + 用户 Profile
- **动作**：填充标准化简历模板，导出 Word (.docx) 文件
- **跨应用**：GLM (内容) -> Microsoft Word (.docx 文件)

### 5. 数据抓取 Skill (Job Scraper)
- **数据源**：驱动 AutoClaw WebDriver 跨平台（BOSS/实习僧/牛客等）抓取实习岗位
- **能力**：自动翻页、平台差异识别、并发抓取、去重
- **跨应用**：Browser -> GLM (解析) -> 标准化 JobItem 列表

### 6. 匹配评分 Skill (Match Scorer)
- **评分引擎**：四维评分体系（技能契合度 40% + 出勤匹配 20% + 城市匹配 20% + 学历匹配 20%）
- **输出**：0-100 匹配分 + Tier 分级（强推荐/推荐/观望）+ 评估理由
- **GLM 委托**：JD 匹配属语义密集型任务，生产环境由 GLM 完成语义级评分

### 7. 报告生成 Skill (Report Generator)
- **动作**：将评分数据写入 Excel，应用条件格式（红/黄/绿评分色块）、冻结标题行、自适应列宽
- **跨应用**：GLM (数据) -> Microsoft Excel (.xlsx 文件)

### 8. 面试出题 Skill (Interview Questioner)
- **输入**：目标岗位类型 + 竞聘能力模型（从 `references/competency_models/` 加载）
- **动作**：基于能力模型生成结构化面试题目，覆盖行为面、专业面、情景面等多个维度
- **输出**：`interview_questions`（结构化题目列表，含考察维度与评分标准提示）
- **能力**：支持多岗位能力模型（管培生、AI产品、后端、前端、数据分析、市场营销等）

### 9. 面试评估 Skill (Interview Scorer)
- **评分引擎**：四维度评分体系
    - **完整性**（25%）：回答是否覆盖题目要点
    - **逻辑性**（25%）：叙述是否条理清晰、因果连贯
    - **STAR 规范度**（25%）：是否遵循 Situation-Task-Action-Result 结构
    - **关键词覆盖**（25%）：是否命中能力模型中的核心关键词
- **输出**：0-100 综合评分 + 各维度分项得分 + 改进建议
- **参考标准**：`references/interview_scoring_criteria.md`

### 10. 面试报告 Skill (Interview Report)
- **输入**：面试题目、用户回答、评分数据、改进建议
- **动作**：生成完整的面试练习报告 Word 文档，包含题目回顾、回答评估、分数雷达图描述、分维度分析与提升建议
- **输出**：`output/面试练习报告.docx`
- **跨应用**：GLM (评估数据) -> Microsoft Word (.docx 文件)

---

## 自动化闭环场景

### 场景一：个性化校招简历生成（JD 定制）
- **用户指令**："这是我大学四年的经历草稿，帮我生成一份针对'管培生'岗位的简历。"
- **执行 Pipeline**：
    1. **JD 分析**：提取管培生岗位的硬技能、软素质、学历要求
    2. **经历萃取**：解析草稿内容，提取时间、角色、行为
    3. **STAR 打磨**：结合 JD 关键词，针对性重构每条经历
    4. **排版导出**：填充 Word 模板，生成排版精美的简历
- **产出结果**：`output/【管培生】姓名_定向简历.docx`

### 场景二：行业实习职位自动聚合
- **用户指令**："帮我找上海的 AI 产品实习。"
- **执行 Pipeline**：
    1. **跨平台抓取**：并发搜索 BOSS、实习僧等平台
    2. **匹配评分**：对比用户画像，对每个岗位打匹配分
    3. **报告生成**：输出《实习申请对比表.xlsx》
- **产出结果**：`output/上海_AI产品实习_实习对比表.xlsx`

### 场景三：模拟面试练习
- **用户指令**："我想练习管培生岗位的面试。"
- **执行 Pipeline**：
    1. **面试出题**：加载管培生能力模型，生成结构化面试题目
    2. **回答评估**：用户逐题作答后，四维度评分并给出改进建议
    3. **报告生成**：输出完整的面试练习报告 Word 文档
- **产出结果**：`output/面试练习报告.docx`

---

## 核心流程 (Pipeline)

| 阶段 | 核心动作 | 对应 Skill 模块 |
|:---|:---|:---|
| **JD 分析** | 提取岗位硬技能、软素质、学历要求 | `skills/jd_analyzer.py` |
| **信息解析** | 解析非结构化草稿，提取关键数据 | `skills/experience_extractor.py` |
| **亮点打磨** | STAR 原则重构，JD 关键词精准覆盖 | `skills/star_polisher.py` |
| **简历排版** | 自动填充模板，导出 Word | `skills/resume_writer.py` |
| **岗位抓取** | 跨平台并发抓取招聘信息 | `skills/web_job_scraper.py` |
| **智能匹配** | 多维度精准打分，过滤低质量岗位 | `skills/match_scorer.py` |
| **报告生成** | 导出 Excel 对比表（含条件格式） | `skills/report_generator.py` |
| **面试出题** | 基于能力模型生成结构化面试题 | `skills/interview_questioner.py` |
| **面试评估** | 四维度评分（完整性/逻辑/STAR/关键词） | `skills/interview_scorer.py` |
| **面试报告** | 导出面试练习报告 Word 文档 | `skills/interview_report.py` |

---

## Pipeline 配置

| Pipeline 名称 | 流程 | 适用场景 |
|:---|:---|:---|
| `resume_generation` | JD 分析 -> 经历萃取 -> STAR 打磨 -> 简历排版 | 定向简历生成 |
| `job_hunting` | 岗位抓取 -> 匹配评分 -> 报告生成 | 实习职位聚合 |
| `interview_practice` | 面试出题 -> 回答评估 -> 报告生成 | 模拟面试练习 |
| `resume_and_interview` | 简历生成 -> 面试练习 | 简历 + 面试一条龙 |

---

## 目录结构

```
Job_Hunting_Copilot_Skill/
├── SKILL.md                       # 赛题说明与 Skill 封装定义（本文件）
├── agent.py                       # Agent 调度引擎（Pipeline 执行器）
├── agent_config.json              # Skill 注册表与 Pipeline 配置
├── cli.py                         # CLI 交互入口
├── requirements.txt               # Python 依赖清单
├── generate_opensource_notice.py  # 开源组件说明文档生成脚本
├── prompts/                       # Prompt 模板管理（热更新）
│   ├── prompt_loader.py           # Prompt 加载器（支持 .md 模板读取）
│   ├── jd_analysis_system.md      # JD 分析系统提示词
│   ├── experience_extract_system.md # 经历萃取系统提示词
│   ├── star_polish_system.md      # STAR 打磨系统提示词
│   ├── star_polish_user.md        # STAR 打磨用户提示词
│   ├── match_scoring_system.md    # 匹配评分系统提示词
│   ├── paper_digest_system.md     # 论文摘要系统提示词
│   ├── interview_question_system.md # 面试出题系统提示词
│   └── interview_score_system.md  # 面试评估系统提示词
├── assets/                        # 存放简历模板与用户经历素材
│   ├── user_resume.json           # 用户画像数据
│   └── resume_template.md         # 简历 Markdown 模板
├── references/                    # 存放 STAR 打磨标准、岗位评分准则
│   ├── resume_standards.md        # 简历内容与打磨规范
│   ├── scoring_criteria.md        # 岗位评估与评分规范
│   ├── interview_scoring_criteria.md # 面试评估评分规范
│   └── competency_models/         # 岗位能力模型（面试出题依据）
│       ├── guanpeisheng.json      # 管培生能力模型
│       ├── ai_product.json        # AI 产品经理能力模型
│       ├── backend.json           # 后端开发能力模型
│       ├── frontend.json          # 前端开发能力模型
│       ├── data_analyst.json      # 数据分析师能力模型
│       └── marketing.json         # 市场营销能力模型
├── skills/                        # Skill 模块（每个文件封装一个独立能力）
│   ├── __init__.py                # AutoClaw Skill 基类
│   ├── jd_analyzer.py             # JD 分析 Skill
│   ├── experience_extractor.py    # 经历萃取 Skill
│   ├── star_polisher.py           # STAR 亮点打磨 Skill
│   ├── resume_writer.py           # 排版适配与 Word 导出 Skill
│   ├── web_job_scraper.py         # 跨平台岗位抓取 Skill
│   ├── match_scorer.py            # 匹配评分 Skill
│   ├── report_generator.py        # Excel 对比表生成 Skill
│   ├── interview_questioner.py    # 面试出题 Skill
│   ├── interview_scorer.py        # 面试评估 Skill
│   └── interview_report.py        # 面试报告生成 Skill
└── output/                        # 存放生成的 Word 简历、Excel 对比表与面试报告
```

## 依赖与工具

- **AutoClaw 框架**：Pipeline 编排、Skill 调度、WebDriver 驱动
- **GLM-4-Plus**：意图识别、语义级 STAR 改写、JD 匹配评分、面试评估
- **python-docx**：Word 简历文件 / 面试练习报告生成
- **pandas / openpyxl**：Excel 对比表生成与格式化
