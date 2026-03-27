from typing import Optional, Protocol

from Backend.Domain.Entities.diagnosis_session import DiagnosisSession
from Backend.Domain.Entities.fault_tree import FaultTree


class FaultTreeGenerationSkill(Protocol):
    """故障树生成 Skill 协议。"""

    # 编写可以用到的接口
    # def generate(self, session: DiagnosisSession) -> Optional[FaultTree]:
    #     """根据诊断会话生成故障树。

    #     Returns:
    #         FaultTree: 当信息充分时返回生成结果
    #         None: 当信息不足以生成故障树
    #     """
    #     ...

    # def get_missing_info(self, session: DiagnosisSession) -> list[str]:
    #     """在信息不足时返回建议补充的信息点列表。"""
    #     ...
