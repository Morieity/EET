import logging
import threading
from collections.abc import Generator

from Backend.Application.Chat.ChatModels import ChatResponseState, FaultTreeIntent
from Backend.Application.Chat.ChatPrompts import (
    build_fault_tree_stream_task_description,
    build_fault_tree_tool_instruction,
)
from Backend.Application.Chat.ChatConfig import FaultTreeGenerationConfig
from Backend.Application.Interfaces.ILLMService import ILLMService
from Backend.Application.Skills.FaultTreeSkill import FaultTreeSkill

logger = logging.getLogger(__name__)


class FaultTreeChatFlow:
    def __init__(
        self,
        llm_service: ILLMService,
        fault_tree_skill: FaultTreeSkill,
        config: FaultTreeGenerationConfig | None = None,
    ):
        self._llm = llm_service
        self._fault_tree_skill = fault_tree_skill
        self._config = config or FaultTreeGenerationConfig()

    def execute(
        self,
        question: str,
        conversation_id: str,
        messages: list[dict],
        system_content: str,
        intent: FaultTreeIntent,
        state: ChatResponseState,
    ) -> Generator[dict, None, None]:
        yield {"type": "generating_tree"}

        tool_messages = self._build_tool_messages(messages, system_content, intent)
        fault_tree_container: list = [None]
        async_done = threading.Event()

        def _generate_fault_tree_async() -> None:
            try:
                tool_result = self._llm.chat_with_tools(
                    tool_messages,
                    self._fault_tree_skill.tools,
                )
                if tool_result["type"] == "tool_call":
                    fault_tree = self._fault_tree_skill.execute(
                        function_name=tool_result["name"],
                        arguments=tool_result["arguments"],
                        conversation_id=conversation_id,
                    )
                    fault_tree_container[0] = fault_tree
                    logger.info(
                        "Fault tree generated: %s (id=%s)",
                        fault_tree.name,
                        fault_tree.id,
                    )
                else:
                    logger.warning(
                        "Fault tree intent detected but model did not call a tool: %s",
                        question,
                    )
            except Exception:
                logger.exception("Fault tree generation failed")
            finally:
                async_done.set()

        thread = threading.Thread(target=_generate_fault_tree_async, daemon=True)
        thread.start()

        stream_messages = self._build_stream_messages(messages, system_content, intent)
        try:
            for token in self._llm.stream_chat(stream_messages):
                state.full_answer += token
                yield {"type": "token", "content": token}
        except Exception:
            logger.exception("LLM stream failed during fault tree request")
            self._attach_fault_tree_if_ready(async_done, fault_tree_container, state)
            if state.fault_tree_id:
                yield {"type": "fault_tree", "fault_tree": fault_tree_container[0].to_dict()}
            state.error_message = "LLM service error"
            return

        self._attach_fault_tree_if_ready(async_done, fault_tree_container, state)
        if state.fault_tree_id:
            yield {"type": "fault_tree", "fault_tree": fault_tree_container[0].to_dict()}
        else:
            err_msg = "\n\n（故障树生成失败，请重试。）"
            state.full_answer += err_msg
            yield {"type": "token", "content": err_msg}
            logger.warning("Async fault tree generation produced no result for: %s", question)

    def _attach_fault_tree_if_ready(
        self,
        async_done: threading.Event,
        fault_tree_container: list,
        state: ChatResponseState,
    ) -> None:
        async_done.wait(timeout=self._config.wait_timeout_seconds)
        if fault_tree_container[0] is not None:
            state.fault_tree_id = fault_tree_container[0].id

    @staticmethod
    def _build_tool_messages(
        messages: list[dict],
        system_content: str,
        intent: FaultTreeIntent,
    ) -> list[dict]:
        tool_instruction = build_fault_tree_tool_instruction(intent.is_update)
        tool_messages = messages.copy()
        tool_messages[0] = {
            "role": "system",
            "content": f"{system_content}\n\n{tool_instruction}",
        }
        return tool_messages

    @staticmethod
    def _build_stream_messages(
        messages: list[dict],
        system_content: str,
        intent: FaultTreeIntent,
    ) -> list[dict]:
        stream_task_desc = build_fault_tree_stream_task_description(intent)
        stream_messages = messages.copy()
        stream_messages[0] = {
            "role": "system",
            "content": f"{system_content}\n\n{stream_task_desc}",
        }
        return stream_messages
