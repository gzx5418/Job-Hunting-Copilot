"""
Prompt 加载器
统一管理所有 Skill 的 Prompt 模板，支持变量占位符替换与缓存。
"""

import os
import logging
from typing import Dict

logger = logging.getLogger("AutoClaw.PromptLoader")

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts")

_cache: Dict[str, str] = {}


def load_prompt(name: str, **variables) -> str:
    """
    加载 Prompt 模板并填充变量。

    :param name: 模板文件名（不含路径，如 "star_polish_system"）
    :param variables: 模板中的 {key} 占位符对应的值
    :return: 填充后的 Prompt 文本
    """
    if name not in _cache:
        filepath = os.path.join(PROMPTS_DIR, f"{name}.md")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                _cache[name] = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt 模板不存在: {filepath}")

    template = _cache[name]

    if variables:
        try:
            return template.format(**variables)
        except KeyError as e:
            logger.warning(f"Prompt 模板 [{name}] 缺少变量: {e}")
            return template

    return template
