# -*- coding: utf-8 -*-
"""
AutoClaw Agent dispatcher.
"""

import importlib
import json
import logging
import os
import sys
from typing import Any, Dict, Optional


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AutoClaw] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("AutoClaw.Agent")

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AGENT_DIR)


class AutoClawAgent:
    def __init__(self, config_path: str = None):
        config_path = config_path or os.path.join(AGENT_DIR, "agent_config.json")
        self.config = self._load_config(config_path)
        self.skill_instances: Dict[str, Any] = {}
        self._load_all_skills()

        meta = self.config["agent_meta"]
        logger.info("=" * 58)
        logger.info(f"  {meta['name']}  |  框架: {meta['framework']}")
        logger.info("  已加载 %d 个 Skill", len(self.skill_instances))
        logger.info(f"  LLM 后端: {meta['llm_backend']}")
        logger.info("=" * 58)

    def _load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise RuntimeError(f"找不到配置文件: {config_path}")

    def _load_all_skills(self):
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

    def route_intent(self, user_input: str) -> Optional[str]:
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

    def _build_output(self, pipeline: Dict[str, Any], context: Dict[str, Any]) -> str:
        output_template = pipeline.get("output", "")
        safe_ctx = {k: str(v) for k, v in context.items() if isinstance(v, (str, int, float))}

        if isinstance(output_template, list):
            final_outputs = []
            for tmpl in output_template:
                try:
                    final_outputs.append(tmpl.format(**safe_ctx))
                except KeyError as e:
                    logger.warning(f"输出模板缺少变量 {e}，跳过替换: {tmpl}")
                    final_outputs.append(tmpl)
            return ", ".join(final_outputs)

        if isinstance(output_template, str):
            try:
                return output_template.format(**safe_ctx)
            except KeyError as e:
                logger.warning(f"输出模板缺少变量 {e}，跳过替换")
                return output_template

        return str(output_template)

    def run_pipeline(self, pipeline_id: str, **init_context) -> Dict:
        pipeline = self.config.get("task_pipelines", {}).get(pipeline_id)
        if not pipeline:
            return {"status": "error", "message": f"未找到 Pipeline: {pipeline_id}"}

        logger.info(f"\n{'=' * 58}")
        logger.info(f"  Pipeline 启动: [{pipeline['name']}]")
        logger.info(f"  {pipeline.get('description', '')}")
        logger.info(f"{'=' * 58}")

        context = dict(init_context)
        step_results: Dict[str, Dict[str, Any]] = {}
        step_errors = []
        steps = pipeline.get("steps", [])

        for step_cfg in steps:
            step_num = step_cfg["step"]
            step_key = f"step_{step_num}"

            if "pipeline" in step_cfg:
                sub_id = step_cfg["pipeline"]
                logger.info(f"\n  [Step {step_num}] >> 执行子 Pipeline: [{sub_id}]")
                try:
                    sub_result = self.run_pipeline(sub_id, **context)
                except Exception as e:
                    logger.error(f"  [X] 子 Pipeline [{sub_id}] 执行异常: {e}")
                    sub_result = {"status": "error", "message": str(e)}

                step_results[step_key] = sub_result
                sub_status = sub_result.get("status")
                if sub_status == "success":
                    context.update(sub_result.get("data", {}))
                elif sub_status == "pending":
                    pending_data = dict(context)
                    pending_data.update(sub_result.get("data", {}))
                    return {
                        "status": "pending",
                        "pipeline": pipeline_id,
                        "pipeline_name": pipeline["name"],
                        "message": sub_result.get("message", f"Sub-pipeline [{sub_id}] pending"),
                        "output": sub_result.get("output", ""),
                        "step_results": step_results,
                        "data": pending_data,
                    }
                else:
                    step_errors.append(sub_result.get("message", f"Sub-pipeline [{sub_id}] failed"))
                    if pipeline.get("fail_fast", False):
                        return {
                            "status": "error",
                            "message": f"子 Pipeline [{sub_id}] 失败: {step_errors[-1]}",
                            "pipeline": pipeline_id,
                            "pipeline_name": pipeline["name"],
                            "step_results": step_results,
                            "data": context,
                        }
                continue

            skill_id = step_cfg.get("skill")
            label = step_cfg.get("label", skill_id)
            logger.info(f"\n  [Step {step_num}/{len(steps)}] > {label}")

            skill = self.skill_instances.get(skill_id)
            if not skill:
                logger.error(f"  [X] Skill [{skill_id}] 未加载，跳过")
                step_results[step_key] = {"status": "error", "message": f"Skill [{skill_id}] 未加载"}
                step_errors.append(f"Skill [{skill_id}] 未加载")
                if pipeline.get("fail_fast", False):
                    return {"status": "error", "message": f"Skill [{skill_id}] 未加载"}
                continue

            try:
                result = skill.run(**context)
            except ValueError as e:
                result = {"status": "error", "message": str(e)}
                logger.error(f"  [X] Skill [{skill_id}] 参数校验失败: {e}")
            except Exception as e:
                result = {"status": "error", "message": str(e)}
                logger.error(f"  [X] Skill [{skill_id}] 执行异常: {e}")

            step_results[step_key] = result

            if result.get("status") == "success":
                result_data = result.get("data", {})
                if isinstance(result_data, dict) and result_data.get("status") in ("pending", "pending_web", "pending_vision", "pending_browser"):
                    pending_data = dict(context)
                    pending_data.update(result_data)
                    logger.info(f"  [PENDING] {result.get('message', '')}")
                    return {
                        "status": "pending",
                        "pipeline": pipeline_id,
                        "pipeline_name": pipeline["name"],
                        "message": result.get("message", ""),
                        "step_results": step_results,
                        "data": pending_data,
                    }

                if isinstance(result_data, dict):
                    context.update(result_data)
                logger.info(f"  [OK] {result.get('message', '')}")
            else:
                logger.error(f"  [X] {result.get('message', '')}")
                step_errors.append(result.get("message", f"Step {step_num} failed"))
                if pipeline.get("fail_fast", False):
                    return {
                        "status": "error",
                        "message": f"Step {step_num} 失败: {result.get('message', '')}",
                        "pipeline": pipeline_id,
                        "pipeline_name": pipeline["name"],
                        "step_results": step_results,
                        "data": context,
                    }

        final_output = self._build_output(pipeline, context)

        logger.info(f"\n{'=' * 58}")
        logger.info(f"  Pipeline [{pipeline['name']}] 完成")
        logger.info(f"  预期输出: {final_output}")
        logger.info(f"{'=' * 58}\n")

        return {
            "status": "error" if step_errors else "success",
            "pipeline": pipeline_id,
            "pipeline_name": pipeline["name"],
            "message": "; ".join(step_errors) if step_errors else "",
            "output": final_output,
            "step_results": step_results,
            "data": context,
        }

    def execute(self, user_input: str, **extra_context) -> Dict:
        pipeline_id = self.route_intent(user_input)
        if not pipeline_id:
            return {
                "status": "fallback",
                "message": "未匹配到 Pipeline，请由 GLM 直接处理。",
                "user_input": user_input,
            }

        init_context = {"user_input": user_input, "raw_text": user_input, **extra_context}
        return self.run_pipeline(pipeline_id, **init_context)

    def run_skill(self, skill_id: str, **kwargs) -> Dict:
        skill = self.skill_instances.get(skill_id)
        if not skill:
            return {"status": "error", "message": f"Skill [{skill_id}] 未加载"}
        try:
            return skill.run(**kwargs)
        except ValueError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}



