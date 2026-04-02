import json
from flask import Blueprint, request, Response
from Backend.Application.UseCases.ChatUseCase import ChatUseCase
from Backend.Application.UseCases.DeleteConversationUseCase import DeleteConversationUseCase
from Backend.Application.Interfaces.IConversationRepository import IConversationRepository

chat_bp = Blueprint("chat", __name__)


def create_chat_blueprint(
    chat_use_case: ChatUseCase,
    delete_conversation_use_case: DeleteConversationUseCase,
    conversation_repository: IConversationRepository,
) -> Blueprint:

    @chat_bp.route("/api/chat", methods=["POST"])
    def chat():
        """SSE 流式对话端点。

        请求体: {"question": str, "conversation_id"?: str}
        SSE 事件流:
          event: conversation  → {"conversation_id": ..., "name": ...}
          event: sources       → {"sources": [...]}
          event: token         → {"content": ...}
          event: done          → {"conversation_id": ..., "answer": ...}
          event: error         → {"message": ...}
        """
        data = request.get_json(silent=True) or {}
        question = data.get("question", "").strip()
        if not question:
            return {"error": "question is required"}, 400

        conversation_id = data.get("conversation_id")

        def event_stream():
            for event in chat_use_case.execute(question, conversation_id):
                event_type = event.pop("type")
                yield f"event: {event_type}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

        return Response(event_stream(), mimetype="text/event-stream")

    @chat_bp.route("/api/conversations", methods=["GET"])
    def list_conversations():
        conversations = conversation_repository.get_all()
        return [c.to_dict() for c in conversations]

    @chat_bp.route("/api/conversations/<conversation_id>", methods=["GET"])
    def get_conversation(conversation_id: str):
        conversation = conversation_repository.get_by_id(conversation_id)
        if conversation is None:
            return {"error": "Conversation not found"}, 404
        return conversation.to_dict()

    @chat_bp.route("/api/conversations/<conversation_id>", methods=["DELETE"])
    def delete_conversation(conversation_id: str):
        try:
            delete_conversation_use_case.execute(conversation_id)
            return {"message": "Conversation deleted"}, 200
        except ValueError as e:
            return {"error": str(e)}, 404

    return chat_bp
