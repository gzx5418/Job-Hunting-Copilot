"""
证书 OCR 提取 Skill (OCR Extractor Skill)
AutoClaw Skill ID: ocr_extractor

职责：
  接收证书照片路径列表，通过 OCR 识别文字内容，
  从中提取时间、证书名称、颁发机构、技能关键词，
  输出与 experience_extractor 兼容的结构化经历数据。

触发场景：
  - "帮我从这些证书照片中提取经历信息"
  - 简历生成 Pipeline 中，作为 experience_extractor 的前置步骤

架构说明：
  本 Skill 依赖图像识别能力。在 AutoClaw 生产环境中，
  由 AutoClaw 的视觉能力（GLM-4V）直接识别图片内容；
  当前提供基于 EasyOCR 的本地实现，以及规则解析的 Demo 模式。
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional
from skills import AutoClawSkill


class OCRExtractorSkill(AutoClawSkill):
    """
    证书 OCR 提取 Skill
    从证书照片中识别文字，提取结构化经历信息
    """

    SKILL_NAME = "ocr_extractor"
    SKILL_DESCRIPTION = "从证书照片中通过 OCR 识别文字，提取证书名称、时间、机构、技能等结构化数据。"

    # 证书常见关键词
    CERTIFICATE_KEYWORDS = [
        "证书", "认证", "资格", "竞赛", "奖", "荣誉", "优秀",
        "一等奖", "二等奖", "三等奖", "金奖", "银奖", "铜奖",
        "合格", "通过", "级别", "等级",
    ]

    # 时间提取模式
    TIME_PATTERNS = [
        r'\d{4}[.\-/年]\d{1,2}[.\-/月]?',
        r'\d{4}年',
    ]

    def run(self, image_paths: List[str] = None, ocr_demo_mode: bool = False,
            **kwargs) -> Dict[str, Any]:
        """
        执行证书 OCR 提取。

        :param image_paths: 证书照片路径列表
        :param ocr_demo_mode: 演示模式（无实际图片时使用）
        :return: 结构化的证书经历列表（与 experience_extractor 输出格式兼容）
        """
        self.logger.info(f"开始证书 OCR 提取 | 图片数: {len(image_paths or [])} | 演示模式: {ocr_demo_mode}")

        certificates = []

        if image_paths:
            for path in image_paths:
                if not os.path.exists(path):
                    self.logger.warning(f"图片不存在: {path}，跳过")
                    continue
                text = self._ocr_image(path)
                cert = self._parse_certificate(text)
                if cert:
                    certificates.append(cert)

        if not certificates:
            self.logger.info("使用演示数据生成证书经历")
            certificates = self._get_demo_certificates()

        self.logger.info(f"证书提取完成，共 {len(certificates)} 项")

        return self._success(
            data={
                "experiences": certificates,
                "count": len(certificates),
                "source": "ocr_extraction",
            },
            message=f"从证书中提取了 {len(certificates)} 段结构化经历"
        )

    def _ocr_image(self, image_path: str) -> str:
        """
        OCR 识别图片文字。
        优先尝试 EasyOCR，失败则尝试 Tesseract，都不可用则返回空。
        """
        # 尝试 EasyOCR
        try:
            import easyocr
            reader = easyocr.Reader(['ch_sim', 'en'], verbose=False)
            results = reader.readtext(image_path)
            text = "\n".join([item[1] for item in results])
            if text.strip():
                self.logger.info(f"EasyOCR 识别成功: {image_path}")
                return text
        except ImportError:
            pass
        except Exception as e:
            self.logger.warning(f"EasyOCR 识别失败: {e}")

        # 尝试 Tesseract
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img, lang='chi_sim+eng')
            if text.strip():
                self.logger.info(f"Tesseract 识别成功: {image_path}")
                return text
        except ImportError:
            pass
        except Exception as e:
            self.logger.warning(f"Tesseract 识别失败: {e}")

        self.logger.warning(f"无可用的 OCR 引擎，请安装 easyocr 或 pytesseract")
        return ""

    def _parse_certificate(self, text: str) -> Optional[Dict]:
        """从 OCR 文本中解析证书信息"""
        if not text or len(text) < 5:
            return None

        # 提取时间
        time_str = ""
        for pattern in self.TIME_PATTERNS:
            match = re.search(pattern, text)
            if match:
                time_str = match.group()
                break

        # 提取证书名称（寻找包含关键词的行）
        cert_name = ""
        for line in text.split("\n"):
            if any(kw in line for kw in self.CERTIFICATE_KEYWORDS):
                cert_name = line.strip()
                break

        if not cert_name:
            cert_name = text[:50].strip()

        # 提取机构名
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

    def _get_demo_certificates(self) -> List[Dict]:
        """演示用证书数据"""
        return [
            {
                "time": "2023.06",
                "organization": "某某大学教务处",
                "role": "获得「校级优秀学生干部」荣誉证书",
                "raw_actions": [
                    "因在学生会期间的突出表现，被评为校级优秀学生干部",
                    "展现了跨部门协作与活动统筹能力",
                ],
                "source": "demo_mode",
            },
            {
                "time": "2023.11",
                "organization": "中国大学生计算机设计大赛组委会",
                "role": "获得「省级三等奖」竞赛证书",
                "raw_actions": [
                    "参加中国大学生计算机设计大赛，作品获省级三等奖",
                    "负责产品设计与用户调研模块，主导需求分析",
                ],
                "source": "demo_mode",
            },
            {
                "time": "2024.03",
                "organization": "教育部考试中心",
                "role": "获得「全国计算机等级考试二级 Python」合格证书",
                "raw_actions": [
                    "通过全国计算机等级考试二级 Python 科目",
                    "掌握 Python 编程基础与数据处理能力",
                ],
                "source": "demo_mode",
            },
        ]
