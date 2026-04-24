"""
证书 OCR 提取 Skill (OCR Extractor Skill)
AutoClaw Skill ID: ocr_extractor

职责：
  接收证书照片路径列表，生成 AutoClaw GLM-4V 视觉识别任务，
  或解析已由 AutoClaw 视觉能力识别的文字内容，
  从中提取时间、证书名称、颁发机构、技能关键词，
  输出与 experience_extractor 兼容的结构化经历数据。

触发场景：
  - "帮我从这些证书照片中提取经历信息"
  - 简历生成 Pipeline 中，作为 experience_extractor 的前置步骤

架构说明：
  本 Skill 依赖 AutoClaw 的视觉能力（GLM-4V）识别图片内容。
  不依赖任何本地 OCR 引擎（EasyOCR/Tesseract），
  完全通过 AutoClaw 框架自带的视觉模型完成识别。
"""

import re
import logging
from typing import List, Dict, Any, Optional
from skills import AutoClawSkill


class OCRExtractorSkill(AutoClawSkill):
    """
    证书 OCR 提取 Skill
    通过 AutoClaw GLM-4V 视觉能力识别证书照片，提取结构化经历信息
    """

    SKILL_NAME = "ocr_extractor"
    SKILL_DESCRIPTION = "通过 AutoClaw GLM-4V 视觉能力识别证书照片，提取证书名称、时间、机构、技能等结构化数据。"

    CERTIFICATE_KEYWORDS = [
        "证书", "认证", "资格", "竞赛", "奖", "荣誉", "优秀",
        "一等奖", "二等奖", "三等奖", "金奖", "银奖", "铜奖",
        "合格", "通过", "级别", "等级",
    ]

    TIME_PATTERNS = [
        r'\d{4}[.\-/年]\d{1,2}[.\-/月]?',
        r'\d{4}年',
    ]

    def run(self, image_paths: List[str] = None,
            ocr_results: Dict[str, str] = None, **kwargs) -> Dict[str, Any]:
        """
        执行证书 OCR 提取。

        :param image_paths: 证书照片路径列表（必需）
        :param ocr_results: AutoClaw GLM-4V 已识别的结果 {path: text}
        :return: 结构化的证书经历列表（与 experience_extractor 输出格式兼容）
        """
        self.validate_input({"image_paths": image_paths}, ["image_paths"])
        self.logger.info(f"开始证书 OCR 提取 | 图片数: {len(image_paths)}")

        certificates: List[Dict] = []

        # 模式A：AutoClaw GLM-4V 已完成识别，直接解析
        if ocr_results:
            for path, text in ocr_results.items():
                if not text:
                    continue
                cert = self._parse_certificate(text)
                if cert:
                    cert["image_path"] = path
                    certificates.append(cert)
                    self.logger.info(f"GLM-4V 识别成功: {path}")

        # 模式B：生成 GLM-4V 视觉识别任务
        if not certificates and image_paths:
            task = self._build_vision_task(image_paths)
            return self._success(
                data={
                    "status": "pending_vision",
                    "vision_task": task,
                    "experiences": [],
                    "count": 0,
                    "source": "ocr_extraction",
                    "message": "已生成 GLM-4V 视觉识别任务，请 AutoClaw 执行后传入 ocr_results"
                },
                message=f"已生成 {len(image_paths)} 张证书的 GLM-4V 视觉识别任务"
            )

        if not certificates:
            self.logger.warning("未能从任何图片中提取到证书信息")

        self.logger.info(f"证书提取完成，共 {len(certificates)} 项")

        return self._success(
            data={
                "experiences": certificates,
                "count": len(certificates),
                "source": "ocr_extraction",
            },
            message=f"从证书中提取了 {len(certificates)} 段结构化经历"
        )

    def _build_vision_task(self, image_paths: List[str]) -> Dict:
        """生成 AutoClaw GLM-4V 视觉识别任务指令"""
        return {
            "action": "ocr_certificates",
            "tool": "GLM-4V",
            "images": image_paths,
            "prompt": (
                "请识别这张证书照片中的所有文字内容，包括："
                "证书名称、颁发时间、颁发机构、持有人姓名、等级/分数、"
                "有效期等所有可见信息。按原始排版输出。"
            ),
            "output_format": "structured_text"
        }

    def _parse_certificate(self, text: str) -> Optional[Dict]:
        """从 OCR 文本中解析证书信息"""
        if not text or len(text) < 5:
            return None

        time_str = ""
        for pattern in self.TIME_PATTERNS:
            match = re.search(pattern, text)
            if match:
                time_str = match.group()
                break

        cert_name = ""
        for line in text.split("\n"):
            if any(kw in line for kw in self.CERTIFICATE_KEYWORDS):
                cert_name = line.strip()
                break
        if not cert_name:
            cert_name = text[:50].strip()

        org = ""
        org_keywords = ["大学", "学院", "协会", "中心", "部门", "组委会", "教育部"]
        for line in text.split("\n"):
            for kw in org_keywords:
                if kw in line:
                    org = line.strip()
                    break
            if org:
                break

        return {
            "time": time_str or "时间待补充",
            "organization": org or "颁发机构待补充",
            "role": f"获得「{cert_name[:30]}」证书" if cert_name else "证书持有者",
            "raw_actions": [f"通过{cert_name}认证" if cert_name else "获得证书认证"],
            "source": "ocr_extraction",
        }
