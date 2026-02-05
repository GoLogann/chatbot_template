import json
import logging

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.core.service.chat.chat_service import ChatService
from app.dependency_injection.application_container import Application
from domain.dto.chat import AskBody

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/chat/completions")
@inject
async def chat_endpoint(
    websocket: WebSocket,
    chat_service: ChatService = Depends(Provide[Application.services.chat_service]),
):
    """
    WebSocket de chat simples sem autenticação.

    Fluxo:
    1. Aceita conexão WebSocket.
    2. Aguarda mensagens contendo {user_id, question, chat_id, session_id}.
    3. Executa o agente e transmite os eventos de resposta ao cliente.
    """
    await websocket.accept()
    last_active_session = None

    try:
        await websocket.send_json({
            "type": "connected",
            "message": "Conexão estabelecida com sucesso"
        })

        while True:
            try:
                raw_msg = await websocket.receive_text()
                data = json.loads(raw_msg)
                payload = AskBody(**data)
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Formato inválido: {str(e)}"
                })
                continue

            async for event in chat_service.run(
                user_id=payload.user_id,
                question=payload.question,
                chat_id=payload.chat_id,
                session_id=payload.session_id,
            ):
                if event.get("type") == "start":
                    last_active_session = {
                        "session_id": event.get("session_id"),
                        "user_id": payload.user_id,
                    }

                logger.debug(f"Enviando evento WebSocket: {event.get('type')}")
                await websocket.send_json(event)

    except WebSocketDisconnect:
        logger.info("Cliente desconectado")

        if last_active_session:
            try:
                chat_service.end_session(
                    last_active_session["user_id"],
                    last_active_session["session_id"],
                )
            except Exception:
                logger.exception("Erro ao encerrar sessão ao desconectar")

    except Exception as e:
        logger.exception("Erro no WebSocket")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
        await websocket.close(code=1011, reason="Internal server error")
