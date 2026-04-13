import json
import logging
from flask import Blueprint, request, Response
from Backend.Application.UseCases.ChatUseCase import ChatUseCase
from Backend.Application.UseCases.DeleteConversationUseCase import DeleteConversationUseCase
from Backend.Application.Interfaces.IConversationRepository import IConversationRepository

chat_bp = Blueprint("chat", __name__)
logger = logging.getLogger(__name__)


def create_chat_blueprint(
    chat_use_case: ChatUseCase,
    delete_conversation_use_case: DeleteConversationUseCase,
    conversation_repository: IConversationRepository,
) -> Blueprint:

    @chat_bp.route("/api/chat", methods=["POST"])
    def chat():
        """SSE 聊天入口。

        实际接收 JSON:
        {
            "question": str,        # strip 后不能为空
            "conversation_id": str, # 可选；继续已有对话时传入
        }

        实际返回 `text/event-stream`，事件内容来自 `ChatUseCase.execute()`:
        - `conversation`: {"conversation_id": str, "name": str}
        - `sources`: {
              "sources": [
                  {"file_name": str, "page_content": str, "score": float},
                  ...
              ]
          }
        - `fault_tree`: {"fault_tree": {...}}
          仅当本轮对话触发故障树工具时发送，`fault_tree` 的结构与
          `/api/fault-trees/<tree_id>` 返回体一致。
        - `token`: {"content": str}
                - `done`: {"conversation_id": str, "answer": str, "fault_tree_id": str | null}
        - `error`: {"message": str}
        """
        data = request.get_json(silent=True) or {}
        question = data.get("question", "").strip()
        if not question:
            return {"error": "question is required"}, 400

        conversation_id = data.get("conversation_id")

        def event_stream():
            try:
                for event in chat_use_case.execute(question, conversation_id):
                    event_type = event.pop("type")
                    yield f"event: {event_type}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            except Exception:
                logger.exception("Unexpected error in SSE stream")
                error_data = json.dumps({"message": "服务器内部错误"}, ensure_ascii=False)
                yield f"event: error\ndata: {error_data}\n\n"

        return Response(
            event_stream(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @chat_bp.route("/api/conversations", methods=["GET"])
    def list_conversations():
        """返回所有对话。

        实际返回的是 `Conversation.to_dict()` 列表；每个元素都包含完整轮次:
        {
            "id": str,
            "name": str,
            "created_at": ISO8601 字符串,
            "rounds": [
                {
                    "id": str,
                    "question": str,
                    "prompt": str,
                    "answer": str,
                    "sources": [
                        {"file_name": str, "page_content": str, "score": float},
                        ...
                    ],
                    "fault_tree_id": str | null,
                    "created_at": ISO8601 字符串,
                },
                ...
            ],
        }
        """
        conversations = conversation_repository.get_all()
        return [c.to_dict() for c in conversations]

    @chat_bp.route("/api/conversations/<conversation_id>", methods=["GET"])
    def get_conversation(conversation_id: str):
        """返回单个对话详情。

        返回体与 `GET /api/conversations` 中单个元素完全一致；找不到时返回:
        {"error": "Conversation not found"}
        """
        conversation = conversation_repository.get_by_id(conversation_id)
        if conversation is None:
            return {"error": "Conversation not found"}, 404
        return conversation.to_dict()

    @chat_bp.route("/api/conversations/<conversation_id>", methods=["DELETE"])
    def delete_conversation(conversation_id: str):
        """删除对话。

        路径参数传的是 `conversation_id`。实际行为不只删除会话，还会级联删除
        与该会话关联的故障树。

        成功返回:
        {"message": "Conversation deleted"}

        会话不存在时返回:
        {"error": "Conversation not found: <conversation_id>"}
        """
        try:
            delete_conversation_use_case.execute(conversation_id)
            return {"message": "Conversation deleted"}, 200
        except ValueError as e:
            return {"error": str(e)}, 404

    return chat_bp
