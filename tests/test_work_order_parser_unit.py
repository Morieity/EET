import io

from openpyxl import Workbook

from Backend.Infrastructure.document.WorkOrderParser import WorkOrderParser


class _StubLLMService:
    def __init__(self, response: str) -> None:
        self._response = response

    def stream_chat(self, messages):
        yield self._response

    def chat_with_tools(self, messages, tools):
        raise NotImplementedError


def test_work_order_parser_parses_csv_with_chinese_headers():
    parser = WorkOrderParser(_StubLLMService("{}"))
    csv_text = (
        "工单编号,设备名称,故障现象,故障原因,故障分类,严重等级,处置措施,发生时间,处理人\n"
        "WO-CSV-001,主泵A,泵体泄漏,密封老化,机械,一般,更换密封圈,2026-04-16 08:30:00,张三\n"
    )

    work_orders, errors = parser.parse_upload(io.BytesIO(csv_text.encode("utf-8")), "orders.csv")

    assert errors == []
    assert len(work_orders) == 1
    work_order = work_orders[0]
    assert work_order.order_no == "WO-CSV-001"
    assert work_order.device_name == "主泵A"
    assert work_order.fault_category == "机械"
    assert work_order.occurrence_time is not None


def test_work_order_parser_parses_xlsx_file():
    parser = WorkOrderParser(_StubLLMService("{}"))
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["工单编号", "设备名称", "故障现象", "处置措施"])
    sheet.append(["WO-XLSX-001", "压缩机B", "温度过高", "清理散热器"])

    buffer = io.BytesIO()
    workbook.save(buffer)
    workbook.close()
    buffer.seek(0)

    work_orders, errors = parser.parse_upload(buffer, "orders.xlsx")

    assert errors == []
    assert len(work_orders) == 1
    assert work_orders[0].order_no == "WO-XLSX-001"
    assert work_orders[0].device_name == "压缩机B"
    assert work_orders[0].solution == "清理散热器"


def test_work_order_parser_parses_text_and_fills_fallbacks():
    parser = WorkOrderParser(
        _StubLLMService(
            """
            {
              "order_no": "",
              "device_name": "",
              "device_code": "EQ-01",
              "fault_phenomenon": "高温报警",
              "fault_cause": "冷却不足",
              "fault_category": "机械",
              "severity": "严重",
              "solution": "清理散热风道",
              "occurrence_time": null,
              "resolution_time": null,
              "operator": "李四",
              "raw_text": ""
            }
            """
        )
    )

    work_order = parser.parse_text("压缩机B高温报警，处理人李四，已清理散热风道。", source_file="manual.txt")

    assert work_order.order_no.startswith("AUTO-")
    assert work_order.device_name == "未知设备"
    assert work_order.device_code == "EQ-01"
    assert work_order.raw_text == "压缩机B高温报警，处理人李四，已清理散热风道。"
    assert work_order.source_file == "manual.txt"
