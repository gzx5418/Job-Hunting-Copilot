"""
AutoClaw Skill 基类
所有 Skill 必须继承此类，实现标准的 run() 接口
GLM 通过此接口统一调度所有 Skill
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger("AutoClaw")


class AutoClawSkill(ABC):
    """
    AutoClaw Skill 基类
    - 每个 Skill 是一个独立的、可组合的业务能力单元
    - GLM 通过调用 run(**kwargs) 驱动每个 Skill 执行
    - Skill 不感知"上下文"，只处理传入的数据
    """

    SKILL_NAME: str = "base_skill"
    SKILL_DESCRIPTION: str = "Base AutoClaw Skill"

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"AutoClaw.{self.SKILL_NAME}")

    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Skill 执行入口 —— 所有子类必须实现
        :return: 包含 status ('success'/'error') 和 data 的字典
        """
        raise NotImplementedError

    def _success(self, data: Any, message: str = "执行成功") -> Dict:
        """标准成功响应格式"""
        self.logger.info(f"✅ [{self.SKILL_NAME}] {message}")
        return {
            "status": "success",
            "skill": self.SKILL_NAME,
            "message": message,
            "data": data
        }

    def _error(self, message: str, detail: str = "") -> Dict:
        """标准失败响应格式"""
        self.logger.error(f"❌ [{self.SKILL_NAME}] {message} | {detail}")
        return {
            "status": "error",
            "skill": self.SKILL_NAME,
            "message": message,
            "detail": detail,
            "data": None
        }

    def validate_input(self, kwargs: Dict, required_keys: list) -> bool:
        """检查必要的输入参数"""
        for key in required_keys:
            if key not in kwargs or kwargs[key] is None:
                raise ValueError(f"Skill [{self.SKILL_NAME}] 缺少必要参数: '{key}'")
        return True
