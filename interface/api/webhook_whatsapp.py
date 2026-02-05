import logging
from typing import Any, Dict

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request

from app.core.config import Settings
from app.core.service.whatsapp.whatsapp_chat_service import WhatsAppChatService
from app.core.service.whatsapp.whatsapp_service import WhatsAppService
from app.dependency_injection.application_container import Application
from domain.dto.whatsapp import WhatsAppWebhookPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["whatsapp"])


@router.get("/whatsapp")
@inject
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    whatsapp_service: WhatsAppService = Depends(
        Provide[Application.whatsapp.whatsapp_service]
    ),
) -> Any:
    """
    Endpoint de verificação do webhook (challenge).

    A Meta chama este endpoint com um GET para verificar que você
    controla o servidor. Deve retornar o hub.challenge se o
    hub.verify_token corresponder ao seu token configurado.

    Query params:
        hub.mode: Deve ser "subscribe"
        hub.challenge: Código a ser retornado
        hub.verify_token: Token a ser verificado

    Returns:
        hub.challenge se verificado, 403 se inválido

    Para configurar no Meta Business Manager:
    1. Vá em Configurações > Webhooks
    2. Configure a URL: https://seu-dominio/webhook/whatsapp
    3. Defina o Verify Token igual ao WHATSAPP_VERIFY_TOKEN no .env
    4. Inscreva-se nos campos: messages
    """
    logger.info(
        f"[WhatsApp Webhook] Verificação recebida: mode={hub_mode}, "
        f"challenge={hub_challenge}, token={hub_verify_token}"
    )

    if hub_mode != "subscribe":
        logger.warning(f"[WhatsApp Webhook] Modo inválido: {hub_mode}")
        raise HTTPException(status_code=403, detail="Invalid mode")

    if not whatsapp_service.verify_webhook_token(hub_verify_token):
        logger.warning("[WhatsApp Webhook] Token de verificação inválido")
        raise HTTPException(status_code=403, detail="Invalid verify token")

    logger.info("[WhatsApp Webhook] Verificação bem-sucedida")
    return int(hub_challenge)


@router.post("/whatsapp")
@inject
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    whatsapp_chat_service: WhatsAppChatService = Depends(
        Provide[Application.whatsapp.whatsapp_chat_service]
    ),
) -> Dict[str, str]:
    """
    Endpoint para recebimento de mensagens do WhatsApp.

    A Meta envia eventos via POST quando:
    - Usuário envia mensagem
    - Mensagem é entregue
    - Mensagem é lida
    - Outros eventos configurados

    O processamento é feito em background para responder
    rapidamente à Meta (evitar timeout).

    Returns:
        {"status": "ok"} - Sempre retorna 200 para a Meta
    """
    try:
        body = await request.json()
        logger.debug(f"[WhatsApp Webhook] Payload recebido: {body}")

        if body.get("object") != "whatsapp_business_account":
            logger.warning(f"[WhatsApp Webhook] Object inválido: {body.get('object')}")
            return {"status": "ok"}

        try:
            payload = WhatsAppWebhookPayload(**body)
        except Exception as e:
            logger.error(f"[WhatsApp Webhook] Erro ao parsear payload: {e}")
            return {"status": "ok"}

        background_tasks.add_task(
            process_webhook_background,
            whatsapp_chat_service,
            payload,
        )

        return {"status": "ok"}

    except Exception as e:
        logger.exception(f"[WhatsApp Webhook] Erro inesperado: {e}")
        return {"status": "ok"}


async def process_webhook_background(
    whatsapp_chat_service: WhatsAppChatService,
    payload: WhatsAppWebhookPayload,
) -> None:
    """
    Processa o webhook em background.

    Args:
        whatsapp_chat_service: Serviço de chat WhatsApp
        payload: Payload do webhook
    """
    try:
        await whatsapp_chat_service.process_webhook(payload)
    except Exception as e:
        logger.exception(f"[WhatsApp Webhook] Erro no processamento background: {e}")
