from typing import Any, List, Optional

from pydantic import BaseModel


class ChatSummary(BaseModel):
    """Resumo de um chat."""
    chat_id: str
    title: str
    updated_at: str
    last_message_preview: Optional[str] = None


class ChatListResponse(BaseModel):
    """Resposta com lista de chats."""
    items: List[ChatSummary]
    last_evaluated_key: Optional[dict] = None


class MessageItem(BaseModel):
    """Item de mensagem."""
    message_id: str
    role: str
    content: str
    created_at: str


class MessagesResponse(BaseModel):
    """Resposta com lista de mensagens."""
    items: List[MessageItem]
    last_evaluated_key: Optional[dict] = None


class SessionItem(BaseModel):
    """Item de sessão."""
    session_id: str
    user_id: str
    chat_id: str
    started_at: str
    ended_at: Optional[str] = None
    is_active: bool


class SessionListResponse(BaseModel):
    """Resposta com lista de sessões."""
    items: List[Any]  # Pode ser tipado melhor depois
    last_evaluated_key: Optional[dict] = None


class UpdateTitlePayload(BaseModel):
    """Payload para atualizar título do chat."""
    title: str
