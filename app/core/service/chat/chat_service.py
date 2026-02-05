import logging
from typing import Any, AsyncIterator, Dict

from app.core.service.llm.graph.orchestrator_agent_service import (
    OrchestratorAgentService,
)
from infra.repositories.chat_repository import ChatRepository

logger = logging.getLogger(__name__)


class ChatService:
    """
    Serviço responsável por orquestrar a comunicação entre o usuário,
    o repositório de chats (DynamoDB) e o agente LLM.

    Este serviço gerencia:
      - Criação e atualização de chats.
      - Início e término de sessões.
      - Envio e registro de mensagens (usuário ↔ assistente).
      - Execução do agente LLM e tratamento dos eventos retornados.
    """

    def __init__(self, llm_service: OrchestratorAgentService, repo: ChatRepository):
        """
        Inicializa o serviço de chat.

        Args:
            llm_service: Serviço LLM responsável por processar prompts e gerar respostas.
            repo: Repositório de dados (ChatRepository) responsável pela persistência no DynamoDB.
        """
        self.llm_service = llm_service
        self.repo = repo

    def start_managed_session(self, user_id: str, chat_id: str) -> Dict[str, Any]:
        """
        Inicia uma nova sessão e encerra quaisquer sessões órfãs (ativas) existentes
        do mesmo usuário para o mesmo chat.

        Args:
            user_id: ID do usuário autenticado.
            chat_id: ID do chat ao qual a sessão pertence.

        Returns:
            Dicionário com os dados da nova sessão iniciada.
        """
        active_sessions = self.repo.list_active_sessions_by_chat(chat_id=chat_id)

        for session in active_sessions.get("items", []):
            if session.get("user_id") == user_id:
                logger.warning(f"Encerrando sessão órfã: {session['session_id']}")
                self.repo.end_session(user_id=user_id, session_id=session["session_id"])

        new_session = self.repo.start_session(user_id=user_id, chat_id=chat_id)
        return new_session

    async def run(
        self,
        user_id: str,
        question: str,
        chat_id: str | None = None,
        session_id: str | None = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Executa o agente LangGraph associado ao chat, processando eventos em tempo real.

        Args:
            user_id: ID do usuário autenticado.
            question: Pergunta ou comando enviado pelo usuário.
            chat_id: (opcional) ID do chat existente. Se não informado, cria um novo.
            session_id: (opcional) ID da sessão ativa. Se não informado, inicia uma nova.

        Yields:
            Eventos em formato JSON, com tipos como:
            - "start": início da sessão e processamento.
            - "token": resposta parcial ou final do assistente.
            - "error": erro ocorrido durante a execução.
            - "end": conclusão do fluxo e persistência da resposta.
        """
        import uuid

        message_id = str(uuid.uuid4())

        if not chat_id:
            title = (question[:50] + "...") if len(question) > 50 else question
            chat = self.repo.create_chat(user_id=user_id, title=title)
            chat_id = chat["chat_id"]
        else:
            # Quando o chat_id é informado, validar existência/posse antes de seguir
            chat_data = self.repo.get_chat(user_id=user_id, chat_id=chat_id)
            if not chat_data:
                yield {
                    "type": "error",
                    "message": "Chat inexistente para este usuário",
                }
                return

        if not session_id:
            sess = self.start_managed_session(user_id=user_id, chat_id=chat_id)
            session_id = sess["session_id"]

        self.repo.append_message(
            chat_id=chat_id, user_id=user_id, role="user", content=question
        )
        try:
            self.repo.update_chat_preview_and_ts(
                user_id=user_id, chat_id=chat_id, preview=question[:160]
            )
        except Exception as e:
            yield {"type": "error", "message": str(e)}
            return
        try:
            self.repo.touch_session(user_id=user_id, session_id=session_id)
        except Exception as e:
            yield {"type": "error", "message": str(e)}
            return

        yield {
            "type": "start",
            "session_id": session_id,
            "chat_id": chat_id,
            "message_id": message_id,
        }

        full_text = ""

        async for event in self.llm_service.execute_agent(
            prompt=question, chat_id=chat_id, session_id=session_id, user_id=user_id
        ):
            event_type = event.get("type")

            if event_type == "agent_response":
                content = event.get("content", "")
                full_text = content

                yield {
                    "type": "agent_response",
                    "message_id": message_id,
                    "content": content,
                }

            elif event_type == "error":
                yield {**event, "message_id": message_id}
                return

        if full_text:
            self.repo.append_message(
                chat_id=chat_id,
                user_id=user_id,
                role="assistant",
                content=full_text,
                msg_id=message_id,
            )
            try:
                self.repo.update_chat_preview_and_ts(
                    user_id=user_id, chat_id=chat_id, preview=full_text[:160]
                )
            except Exception as e:
                yield {"type": "error", "message": str(e)}
                return

        yield {
            "type": "end",
            "message_id": message_id,
            "session_id": session_id,
            "chat_id": chat_id,
            "full_text": full_text,
        }

    def end_session(self, user_id: str, session_id: str):
        """Encerra uma sessão ativa de chat."""
        self.repo.end_session(user_id, session_id)

    def list_chats(self, user_id: str, limit: int = 20, cursor: dict | None = None):
        """Lista os chats de um usuário autenticado."""
        return self.repo.list_chats(user_id, limit, cursor)

    def history(self, chat_id: str, limit: int = 100, cursor: dict | None = None):
        """Retorna o histórico completo (mensagens) de um chat."""
        return self.repo.get_messages(chat_id, limit, cursor)

    def update_chat_title(self, user_id: str, chat_id: str, new_title: str):
        """Atualiza o título de um chat existente."""
        self.repo.update_chat_title(
            user_id=user_id, chat_id=chat_id, new_title=new_title
        )

    def list_sessions(self, chat_id: str, limit: int = 50, cursor: dict | None = None):
        """Lista todas as sessões (ativas ou encerradas) de um chat."""
        return self.repo.list_sessions_by_chat(chat_id, limit, cursor)
