# -*- coding: utf-8 -*-
"""
AutoClaw Agent 调度引擎 (GLM Pipeline Dispatcher)  v2.1
========================================================
核心文件：agent.py

职责：
  1. 加载 agent_config.json 中的 Skill 注册表和 Pipeline 定义
  2. 接收用户自然语言指令
  3. 通过意图路由规则，将指令映射到对应的 Pipeline
  4. 按 Pipeline 步骤顺序调度各 Skill 执行
  5. 管理 Skill 间的数据流（上一步输出 → 下一步输入）
  6. 汇总最终输出，报告结果给用户

架构图：
  用户指令
     │
     ▼
  GLM 意图识别 & 路由 (route_intent)
     │
     ▼
  Pipeline 定义 (agent_config.json)
  ┌──────────────────────────────┐
  │  Step 1 → Skill A (run())   │
  │  Step 2 → Skill B (run())   │  ← 数据流自动传递
  │  Step 3 → Skill C (run())   │
  └──────────────────────────────┘
     │
     ▼
  输出文件 (output/ 目录)
"""

import json
import os
import sys
import importlib
import logging
from typing import Any, Dict, Optional, List

# ── 日志配置 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AutoClaw] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("AutoClaw.Agent")

# ── 将 Skill 模块目录加入 Python 路径 ──
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AGENT_DIR)


class AutoClawAgent:
    """
    AutoClaw Agent 调度引擎

    通过配置文件（agent_config.json）驱动整个 Agent 的行为：
    - 所有 Skill 在配置文件中注册，引擎动态加载
    - 新增/修改能力只需编辑配置文件，无需修改此引擎
    - GLM 作为"大脑"负责理解意图，Agent 作为"执行者"负责调度 Skill
    """

    def __init__(self, config_path: str = None):
        config_path = config_path or os.path.join(AGENT_DIR, "agent_config.json")
        self.config = self._load_config(config_path)
        self.skill_instances: Dict[str, Any] = {}
        self._load_all_skills()

        meta = self.config["agent_meta"]
        logger.info("=" * 58)
        logger.info(f"  {meta['name']}  |  框架: {meta['framework']}")
        logger.info(f"  已加载 %d 个 Skill", len(self.skill_instances))
        logger.info(f"  LLM 后端: {meta['llm_backend']}")
        logger.info("=" * 58)

    # ──────────────────────────────────────────────────
    #  初始化
    # ──────────────────────────────────────────────────

    def _load_config(self, config_path: str) -> Dict:
        """加载 agent_config.json"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise RuntimeError(f"找不到配置文件: {config_path}")

    def _load_all_skills(self):
        """
        按 skill_registry 动态加载所有 Skill 类。
        实现热插拔：新增 Skill 只需在 agent_config.json 注册，无需修改此引擎。
        """
        registry = self.config.get("skill_registry", {})
        runtime = self.config.get("runtime_settings", {})
        loaded, failed = [], []

        for skill_id, skill_meta in registry.items():
            try:
                module = importlib.import_module(skill_meta["module"])
                skill_class = getattr(module, skill_meta["class"])
                self.skill_instances[skill_id] = skill_class(config=runtime)
                loaded.append(skill_id)
            except (ImportError, AttributeError, ModuleNotFoundError) as e:
                failed.append(f"{skill_id} ({e})")

        if loaded:
            logger.info(f"  成功加载: {', '.join(loaded)}")
        if failed:
            logger.warning(f"  加载失败: {'; '.join(failed)}")

    # ──────────────────────────────────────────────────
    #  意图路由
    # ──────────────────────────────────────────────────

    def route_intent(self, user_input: str) -> Optional[str]:
        """
        意图路由：将用户自然语言映射到 Pipeline ID。
        生产环境中此步骤由 GLM 完成语义级匹配，
        此处提供关键词规则路由作为轻量 Demo 实现。

        :param user_input: 用户自然语言指令
        :return: pipeline_id 或 None（fallback 给 GLM 直接回答）
        """
        routing_rules = self.config.get("llm_dispatch_rules", {}).get("routing", [])
        best_match, best_score = None, 0

        for rule in routing_rules:
            score = sum(1 for kw in rule.get("keywords", []) if kw in user_input)
            if score > best_score:
                best_score = score
                best_match = rule["pipeline"]

        if best_match and best_score > 0:
            logger.info(f"[路由] 意图匹配: [{best_match}]（命中 {best_score} 个关键词）")
        else:
            logger.info("[路由] 未匹配到 Pipeline，降级为 GLM 直接回答")

        return best_match if best_score > 0 else None

    # ──────────────────────────────────────────────────
    #  Pipeline 执行
    # ──────────────────────────────────────────────────

    def run_pipeline(self, pipeline_id: str, **init_context) -> Dict:
        """
        按配置执行指定的 Pipeline。

        数据流机制：
          每个 Skill 的 run(**context) 接收当前上下文；
          Skill 的 data 输出会合并入 context，传递给下一个 Skill。

        :param pipeline_id: Pipeline ID
        :param init_context: 初始上下文数据
        :return: 最终执行结果摘要
        """
        pipeline = self.config.get("task_pipelines", {}).get(pipeline_id)
        if not pipeline:
            return {"status": "error", "message": f"未找到 Pipeline: {pipeline_id}"}

        logger.info(f"\n{'=' * 58}")
        logger.info(f"  Pipeline 启动: [{pipeline['name']}]")
        logger.info(f"  {pipeline.get('description', '')}")
        logger.info(f"{'=' * 58}")

        context = dict(init_context)
        step_results = {}
        steps = pipeline.get("steps", [])

        for step_cfg in steps:
            step_num = step_cfg["step"]

            # 支持嵌套 Pipeline
            if "pipeline" in step_cfg:
                sub_id = step_cfg["pipeline"]
                logger.info(f"\n  [Step {step_num}] >> 执行子 Pipeline: [{sub_id}]")
                try:
                    sub_result = self.run_pipeline(sub_id, **context)
                    context.update(sub_result.get("data", {}))
                    step_results[f"step_{step_num}"] = sub_result
                except Exception as e:
                    logger.error(f"  [X] 子 Pipeline [{sub_id}] 执行异常: {e}")
                    step_results[f"step_{step_num}"] = {"status": "error", "message": str(e)}
                    if pipeline.get("fail_fast", False):
                        return {"status": "error", "message": f"子 Pipeline [{sub_id}] 失败: {e}"}
                continue

            skill_id = step_cfg.get("skill")
            label = step_cfg.get("label", skill_id)
            logger.info(f"\n  [Step {step_num}/{len(steps)}] > {label}")

            skill = self.skill_instances.get(skill_id)
            if not skill:
                logger.error(f"  [X] Skill [{skill_id}] 未加载，跳过")
                if pipeline.get("fail_fast", False):
                    return {"status": "error", "message": f"Skill [{skill_id}] 未加载"}
                continue

            # 执行 Skill
            try:
                result = skill.run(**context)
            except ValueError as e:
                result = {"status": "error", "message": str(e)}
                logger.error(f"  [X] Skill [{skill_id}] 参数校验失败: {e}")
            except Exception as e:
                result = {"status": "error", "message": str(e)}
                logger.error(f"  [X] Skill [{skill_id}] 执行异常: {e}")

            step_results[f"step_{step_num}"] = result

            if result.get("status") == "success":
                context.update(result.get("data", {}))
                logger.info(f"  [OK] {result.get('message', '')}")
            else:
                logger.error(f"  [X] {result.get('message', '')}")
                if pipeline.get("fail_fast", False):
                    return {"status": "error", "message": f"Step {step_num} 失败: {result.get('message', '')}"}

        # 渲染输出路径模板
        output_template = pipeline.get("output", "")
        safe_ctx = {k: str(v) for k, v in context.items() if isinstance(v, (str, int, float))}
        if isinstance(output_template, list):
            final_outputs = []
            for tmpl in output_template:
                try:
                    final_outputs.append(tmpl.format(**safe_ctx))
                except KeyError:
                    final_outputs.append(tmpl)
            final_output = ", ".join(final_outputs)
        elif isinstance(output_template, str):
            try:
                final_output = output_template.format(**safe_ctx)
            except KeyError:
                final_output = output_template
        else:
            final_output = str(output_template)

        logger.info(f"\n{'=' * 58}")
        logger.info(f"  Pipeline [{pipeline['name']}] 完成")
        logger.info(f"  预期输出: {final_output}")
        logger.info(f"{'=' * 58}\n")

        return {
            "status": "success",
            "pipeline": pipeline_id,
            "pipeline_name": pipeline["name"],
            "output": final_output,
            "step_results": step_results,
            "data": context
        }

    # ──────────────────────────────────────────────────
    #  主入口
    # ──────────────────────────────────────────────────

    def execute(self, user_input: str, **extra_context) -> Dict:
        """
        Agent 主入口：接收用户指令，自动路由并执行 Pipeline。

        :param user_input: 用户自然语言指令
        :param extra_context: 可选的结构化上下文（target_role、city 等）
        :return: 执行结果摘要
        """
        pipeline_id = self.route_intent(user_input)
        if not pipeline_id:
            return {
                "status": "fallback",
                "message": "未匹配到 Pipeline，请由 GLM 直接处理。",
                "user_input": user_input
            }

        init_context = {"user_input": user_input, "raw_text": user_input, **extra_context}
        return self.run_pipeline(pipeline_id, **init_context)


# ══════════════════════════════════════════════════════
#  演示入口
# ══════════════════════════════════════════════════════

def demo_resume_generation(agent: AutoClawAgent):
    """演示场景一：个性化校招简历生成（JD 定制）"""
    print("\n" + "-" * 58)
    print("  [场景一] 案例 2 -- 个性化校招简历生成助手（JD 定制版）")
    print("-" * 58)

    result = agent.execute(
        user_input="这是我大学四年的经历草稿，帮我生成一份针对'管培生'岗位的简历。",
        target_role="管培生",
        jd_text=(
            "管培生岗位要求：本科及以上学历，专业不限。具备较强的沟通协调能力、"
            "学习能力和抗压能力。有学生干部经验优先。熟练使用 Excel、PPT 等办公软件。"
            "具有跨部门协作经验，善于解决问题，有领导力潜质。每周 5 天，实习 3 个月以上。"
        ),
        raw_text=(
            "大二加入了学生会文艺部，做了一年干事，期间办了迎新晚会，"
            "拉了2000块钱赞助，还写了几篇推文。\n\n"
            "大三暑假去了一家互联网公司实习，主要工作是回复用户消息，"
            "建了几个微信群，整理过各种表格。\n\n"
            "大四参加了大创项目，我们组做了一个校园互助小程序，"
            "我主要负责产品方向的需求整理和用户调研。"
        )
    )
    if result.get("status") == "success":
        print("\n  [OK] 场景一完成！")
        file_path = result.get("data", {}).get("file_path", result.get("output", ""))
        if file_path:
            print(f"  [FILE] 简历文件: {file_path}")
    return result


def demo_internship_aggregator(agent: AutoClawAgent):
    """演示场景二：行业实习职位自动聚合器"""
    print("\n" + "-" * 58)
    print("  [场景二] 案例 3 -- 行业实习职位自动聚合器")
    print("-" * 58)

    result = agent.execute(
        user_input="帮我找上海的 AI 产品实习，跨平台抓取并生成对比表。",
        keyword="AI 产品实习",
        city="上海",
        platforms=["zhipin", "shixiseng", "nowcoder"]
    )
    if result.get("status") == "success":
        print("\n  [OK] 场景二完成！")
        file_path = result.get("data", {}).get("file_path", result.get("output", ""))
        if file_path:
            print(f"  [FILE] 对比表: {file_path}")
    return result


def main():
    print("\n" + "=" * 58)
    print("  AutoClaw Agent -- 求职智能体  |  全流程演示")
    print("  框架: AutoClaw  |  LLM: GLM-4-Plus")
    print("=" * 58)

    config_path = os.path.join(AGENT_DIR, "agent_config.json")
    agent = AutoClawAgent(config_path=config_path)

    # 演示两大核心场景
    demo_resume_generation(agent)
    demo_internship_aggregator(agent)

    print("\n" + "=" * 58)
    print("  [DONE] 全流程演示完成！请查看 output/ 目录中的生成文件")
    print("=" * 58 + "\n")


if __name__ == "__main__":
    main()
