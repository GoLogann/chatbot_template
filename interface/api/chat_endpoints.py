from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

from app.core.service.chat.chat_service import ChatService
from app.dependency_injection.application_container import Application
from domain.dto.responses import (
    ChatListResponse,
    ChatSummary,
    MessageItem,
    MessagesResponse,
    SessionListResponse,
    UpdateTitlePayload,
)

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.get("/", response_model=ChatListResponse)
@inject
def list_chats(
    user_id: str = Query(..., description="ID do usuário"),
    limit: int = 20,
    cursor: dict | None = None,
    svc: ChatService = Depends(Provide[Application.services.chat_service]),
):
    """
    Lista todos os chats do usuário.

    Args:
        user_id: ID do usuário.
        limit: Quantidade máxima de registros a retornar (default: 20).
        cursor: Ponto de paginação opcional (DynamoDB ExclusiveStartKey).
        svc: Instância do ChatService injetada via container.

    Returns:
        ChatListResponse contendo lista de chats e chave de continuação.
    """
    res = svc.list_chats(user_id=user_id, limit=limit, cursor=cursor)

    items = [
        ChatSummary(
            chat_id=i["chat_id"],
            title=i["title"],
            updated_at=i["updated_at"],
            last_message_preview=i.get("last_message_preview"),
        )
        for i in res["items"]
    ]

    return ChatListResponse(
        items=items,
        last_evaluated_key=res.get("last_evaluated_key"),
    )


@router.get("/{chat_id}/messages", response_model=MessagesResponse)
@inject
def get_messages(
    chat_id: str,
    limit: int = 100,
    cursor: dict | None = None,
    svc: ChatService = Depends(Provide[Application.services.chat_service]),
):
    """
    Lista as mensagens de um chat específico.

    Args:
        chat_id: Identificador do chat.
        limit: Quantidade máxima de mensagens a retornar.
        cursor: Ponto de paginação opcional.
        svc: Serviço de chat.

    Returns:
        MessagesResponse com mensagens e cursor de continuação.
    """
    res = svc.history(chat_id=chat_id, limit=limit, cursor=cursor)

    items = [
        MessageItem(
            message_id=i["message_id"],
            role=i["role"],
            content=i["content"],
            created_at=i["created_at"],
        )
        for i in res["items"]
    ]

    return MessagesResponse(
        items=items,
        last_evaluated_key=res.get("last_evaluated_key"),
    )


@router.get("/{chat_id}/sessions", response_model=SessionListResponse)
@inject
def list_sessions(
    chat_id: str,
    limit: int = 50,
    cursor: dict | None = None,
    svc: ChatService = Depends(Provide[Application.services.chat_service]),
):
    """
    Lista as sessões de um chat específico.

    Args:
        chat_id: ID do chat.
        limit: Quantidade máxima de sessões.
        cursor: Ponto de paginação opcional.
        svc: Serviço de chat.

    Returns:
        SessionListResponse contendo as sessões do chat.
    """
    res = svc.list_sessions(chat_id=chat_id, limit=limit, cursor=cursor)

    return SessionListResponse(
        items=res["items"],
        last_evaluated_key=res.get("last_evaluated_key"),
    )


@router.patch("/{chat_id}/title", status_code=status.HTTP_204_NO_CONTENT)
@inject
def update_chat_title(
    chat_id: str,
    user_id: str = Query(..., description="ID do usuário"),
    payload: UpdateTitlePayload = ...,
    svc: ChatService = Depends(Provide[Application.services.chat_service]),
):
    """
    Atualiza o título de um chat específico.

    Args:
        chat_id: ID do chat a ser atualizado.
        user_id: ID do usuário dono do chat.
        payload: Novo título (DTO).
        svc: Serviço de chat.
    """
    svc.update_chat_title(user_id=user_id, chat_id=chat_id, new_title=payload.title)
