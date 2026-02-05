import logging
from typing import Any, Dict, Optional

from app.core.config import Settings
from app.core.service.chat.chat_service import ChatService
from app.core.service.whatsapp.whatsapp_service import WhatsAppService
from domain.dto.whatsapp import WhatsAppWebhookPayload
from infra.repositories.chat_repository import ChatRepository

logger = logging.getLogger(__name__)


class WhatsAppChatService:
    """
    Serviço de integração WhatsApp + ChatService.

    Este serviço atua como ponte entre o webhook do WhatsApp e o
    ChatService existente, permitindo usar a mesma lógica de
    conversação para múltiplos canais (WebSocket, WhatsApp, etc).

    Funcionalidades:
    - Gerenciamento de sessão por número de telefone
    - Processamento assíncrono de mensagens
    - Controle de estado da conversa
    - Mapeamento de usuários WhatsApp para users internos

    Exemplo:
        service = WhatsAppChatService(
            settings=settings,
            chat_service=chat_service,
            whatsapp_service=whatsapp_service,
            repo=chat_repository
        )
        await service.process_webhook(payload)
    """

    def __init__(
        self,
        settings: Settings,
        chat_service: ChatService,
        whatsapp_service: WhatsAppService,
        repo: ChatRepository,
    ):
        """
        Inicializa o serviço de chat WhatsApp.

        Args:
            settings: Configurações da aplicação
            chat_service: Serviço de chat principal
            whatsapp_service: Serviço de envio WhatsApp
            repo: Repositório para persistência
        """
        self.settings = settings
        self.chat_service = chat_service
        self.whatsapp_service = whatsapp_service
        self.repo = repo

        # Cache simples de sessões (em produção, use Redis ou DynamoDB)
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def _get_user_id_from_phone(self, phone: str) -> str:
        """
        Gera um user_id único baseado no número de telefone.

        Em produção, você pode querer:
        - Buscar usuário existente no banco de dados
        - Criar novo usuário se não existir
        - Vincular a uma conta existente

        Args:
            phone: Número de telefone (ex: 5511999999999)

        Returns:
            User ID único
        """
        return f"whatsapp_{phone}"

    def _get_or_create_session(self, phone: str) -> Dict[str, Any]:
        """
        Obtém ou cria uma sessão para o número de telefone.

        A sessão armazena:
        - user_id: ID interno do usuário
        - chat_id: ID do chat atual
        - session_id: ID da sessão ativa
        - name: Nome do contato (se disponível)

        Args:
            phone: Número de telefone

        Returns:
            Dict com dados da sessão
        """
        if phone not in self._sessions:
            user_id = self._get_user_id_from_phone(phone)
            self._sessions[phone] = {
                "user_id": user_id,
                "chat_id": None,
                "session_id": None,
                "name": None,
            }
            logger.info(f"[WhatsAppChat] Nova sessão criada para {phone}")

        return self._sessions[phone]

    def _update_session(
        self,
        phone: str,
        chat_id: Optional[str] = None,
        session_id: Optional[str] = None,
        name: Optional[str] = None,
    ):
        """Atualiza dados da sessão."""
        session = self._get_or_create_session(phone)

        if chat_id:
            session["chat_id"] = chat_id
        if session_id:
            session["session_id"] = session_id
        if name:
            session["name"] = name

        self._sessions[phone] = session

    async def process_webhook(self, payload: WhatsAppWebhookPayload) -> None:
        """
        Processa um payload de webhook do WhatsApp.

        Este método:
        1. Extrai todas as mensagens do payload
        2. Para cada mensagem de texto:
           - Marca como lida
           - Obtém/cria sessão
           - Processa via ChatService
           - Envia resposta via WhatsApp

        Args:
            payload: Payload completo do webhook
        """
        messages = payload.get_messages()

        if not messages:
            logger.debug("[WhatsAppChat] Webhook sem mensagens de texto")
            return

        for msg in messages:
            await self._process_message(msg)

    async def _process_message(self, msg: Dict[str, Any]) -> None:
        """
        Processa uma única mensagem do WhatsApp.

        Args:
            msg: Dict com dados da mensagem:
                - phone: número do remetente
                - name: nome do contato
                - message_id: ID da mensagem
                - text: conteúdo (se texto)
                - type: tipo da mensagem
        """
        phone = msg.get("phone")
        name = msg.get("name")
        message_id = msg.get("message_id")
        text = msg.get("text")
        msg_type = msg.get("type")

        logger.info(
            f"[WhatsAppChat] Mensagem recebida de {phone} ({name}): "
            f"type={msg_type}, text={text[:50] if text else 'N/A'}..."
        )

        # Marca mensagem como lida
        await self.whatsapp_service.mark_as_read(message_id)

        # Ignora mensagens que não são de texto
        if msg_type != "text" or not text:
            logger.debug(f"[WhatsAppChat] Ignorando mensagem tipo {msg_type}")
            # Opcionalmente, envie uma mensagem informando tipos suportados
            # await self.whatsapp_service.send_text(
            #     phone, "Desculpe, no momento só consigo processar mensagens de texto."
            # )
            return

        # Obtém ou cria sessão
        session = self._get_or_create_session(phone)
        self._update_session(phone, name=name)

        user_id = session["user_id"]
        chat_id = session.get("chat_id")
        session_id = session.get("session_id")

        # Processa via ChatService
        full_response = ""

        try:
            async for event in self.chat_service.run(
                user_id=user_id,
                question=text,
                chat_id=chat_id,
                session_id=session_id,
            ):
                event_type = event.get("type")

                if event_type == "start":
                    # Atualiza IDs da sessão
                    self._update_session(
                        phone,
                        chat_id=event.get("chat_id"),
                        session_id=event.get("session_id"),
                    )

                elif event_type == "agent_response":
                    full_response = event.get("content", "")

                elif event_type == "error":
                    error_msg = event.get("message", "Erro desconhecido")
                    logger.error(f"[WhatsAppChat] Erro no ChatService: {error_msg}")
                    full_response = (
                        "Desculpe, ocorreu um erro ao processar sua mensagem. "
                        "Por favor, tente novamente."
                    )

                elif event_type == "end":
                    # Atualiza sessão com IDs finais
                    self._update_session(
                        phone,
                        chat_id=event.get("chat_id"),
                        session_id=event.get("session_id"),
                    )

        except Exception as e:
            logger.exception(f"[WhatsAppChat] Erro ao processar mensagem: {e}")
            full_response = (
                "Desculpe, ocorreu um erro inesperado. Por favor, tente novamente."
            )

        # Envia resposta via WhatsApp
        if full_response:
            await self.whatsapp_service.send_text(phone, full_response)
            logger.info(f"[WhatsAppChat] Resposta enviada para {phone}")

    async def handle_text_message(
        self,
        phone: str,
        text: str,
        name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Processa uma mensagem de texto diretamente (sem payload de webhook).

        Útil para:
        - Testes
        - Integração com outros sistemas
        - Mensagens proativas

        Args:
            phone: Número de telefone
            text: Texto da mensagem
            name: Nome do contato (opcional)

        Returns:
            Resposta gerada ou None se erro
        """
        msg = {
            "phone": phone,
            "name": name or "Unknown",
            "message_id": f"manual_{phone}_{text[:10]}",
            "text": text,
            "type": "text",
        }

        # Extrai resposta (sem enviar via WhatsApp automaticamente)
        session = self._get_or_create_session(phone)
        self._update_session(phone, name=name)

        user_id = session["user_id"]
        chat_id = session.get("chat_id")
        session_id = session.get("session_id")

        full_response = ""

        async for event in self.chat_service.run(
            user_id=user_id,
            question=text,
            chat_id=chat_id,
            session_id=session_id,
        ):
            event_type = event.get("type")

            if event_type == "start":
                self._update_session(
                    phone,
                    chat_id=event.get("chat_id"),
                    session_id=event.get("session_id"),
                )
            elif event_type == "agent_response":
                full_response = event.get("content", "")
            elif event_type == "end":
                self._update_session(
                    phone,
                    chat_id=event.get("chat_id"),
                    session_id=event.get("session_id"),
                )

        return full_response if full_response else None

    def clear_session(self, phone: str) -> bool:
        """
        Limpa a sessão de um usuário.

        Útil quando o usuário quer reiniciar a conversa.

        Args:
            phone: Número de telefone

        Returns:
            True se sessão foi removida
        """
        if phone in self._sessions:
            del self._sessions[phone]
            logger.info(f"[WhatsAppChat] Sessão removida para {phone}")
            return True
        return False

    def get_session_info(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Retorna informações da sessão de um usuário.

        Args:
            phone: Número de telefone

        Returns:
            Dict com dados da sessão ou None
        """
        return self._sessions.get(phone)
