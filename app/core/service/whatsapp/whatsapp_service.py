import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)

WHATSAPP_API_BASE = "https://graph.facebook.com/v18.0"


class WhatsAppService:
    """
    Serviço para interação com a Meta WhatsApp Cloud API.

    Responsabilidades:
    - Enviar mensagens de texto
    - Enviar mensagens de template
    - Marcar mensagens como lidas
    - Gerenciar estados de digitação

    Requisitos:
    - WHATSAPP_PHONE_NUMBER_ID: ID do número de telefone no Meta Business
    - WHATSAPP_ACCESS_TOKEN: Token de acesso da API

    Exemplo:
        service = WhatsAppService(settings)
        await service.send_text("5511999999999", "Olá!")
    """

    def __init__(self, settings: Settings):
        """
        Inicializa o serviço do WhatsApp.

        Args:
            settings: Configurações da aplicação
        """
        self.settings = settings
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN

        self.enabled = bool(self.phone_number_id and self.access_token)

        if not self.enabled:
            logger.warning(
                "[WhatsAppService] Serviço desabilitado. "
                "Configure WHATSAPP_PHONE_NUMBER_ID e WHATSAPP_ACCESS_TOKEN."
            )

    def _get_headers(self) -> Dict[str, str]:
        """Retorna headers para requisições à API."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _get_messages_url(self) -> str:
        """Retorna URL do endpoint de mensagens."""
        return f"{WHATSAPP_API_BASE}/{self.phone_number_id}/messages"

    async def send_text(
        self,
        to: str,
        text: str,
        preview_url: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Envia uma mensagem de texto.

        Args:
            to: Número de destino (formato: 5511999999999)
            text: Conteúdo da mensagem
            preview_url: Se True, gera preview de URLs na mensagem

        Returns:
            Resposta da API ou None se erro/desabilitado
        """
        if not self.enabled:
            logger.warning("[WhatsAppService] Serviço desabilitado, mensagem não enviada")
            return None

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": text,
            },
        }

        return await self._send_request(payload)

    async def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str = "pt_BR",
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Envia uma mensagem de template (HSM).

        Templates devem ser pré-aprovados no Meta Business Manager.

        Args:
            to: Número de destino
            template_name: Nome do template aprovado
            language_code: Código do idioma (ex: pt_BR, en_US)
            components: Componentes dinâmicos (header, body, buttons)

        Returns:
            Resposta da API ou None se erro/desabilitado

        Exemplo de components:
            components = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": "João"},
                        {"type": "text", "text": "12345"}
                    ]
                }
            ]
        """
        if not self.enabled:
            logger.warning("[WhatsAppService] Serviço desabilitado, template não enviado")
            return None

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }

        if components:
            payload["template"]["components"] = components

        return await self._send_request(payload)

    async def mark_as_read(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Marca uma mensagem como lida.

        Isso envia os ticks azuis para o usuário.

        Args:
            message_id: ID da mensagem a ser marcada

        Returns:
            Resposta da API ou None se erro/desabilitado
        """
        if not self.enabled:
            return None

        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }

        return await self._send_request(payload)

    async def send_typing_indicator(self, to: str) -> Optional[Dict[str, Any]]:
        """
        Envia indicador de "digitando..." para o usuário.

        Nota: Esta funcionalidade pode não estar disponível em todas as versões da API.

        Args:
            to: Número de destino

        Returns:
            Resposta da API ou None se erro/desabilitado
        """
        if not self.enabled:
            return None

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "reaction",
        }

        # Nota: A API pode não suportar typing indicator diretamente
        # Considere implementar via webhook de status
        logger.debug(f"[WhatsAppService] Typing indicator para {to}")
        return None

    async def _send_request(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Envia requisição para a API do WhatsApp.

        Args:
            payload: Corpo da requisição

        Returns:
            Resposta JSON da API ou None se erro
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self._get_messages_url(),
                    headers=self._get_headers(),
                    json=payload,
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(
                        f"[WhatsAppService] Mensagem enviada com sucesso. "
                        f"Message ID: {data.get('messages', [{}])[0].get('id', 'N/A')}"
                    )
                    return data
                else:
                    logger.error(
                        f"[WhatsAppService] Erro ao enviar mensagem. "
                        f"Status: {response.status_code}, Body: {response.text}"
                    )
                    return None

        except httpx.TimeoutException:
            logger.error("[WhatsAppService] Timeout ao enviar mensagem")
            return None
        except Exception as e:
            logger.exception(f"[WhatsAppService] Erro inesperado: {e}")
            return None

    def verify_webhook_token(self, token: str) -> bool:
        """
        Verifica se o token do webhook é válido.

        Args:
            token: Token recebido no webhook

        Returns:
            True se o token é válido
        """
        expected_token = self.settings.WHATSAPP_VERIFY_TOKEN
        if not expected_token:
            logger.warning("[WhatsAppService] WHATSAPP_VERIFY_TOKEN não configurado")
            return False
        return token == expected_token
