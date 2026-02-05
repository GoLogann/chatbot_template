import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

ISO = "%Y-%m-%dT%H:%M:%S.%fZ"


def now_iso() -> str:
    """Retorna timestamp atual em formato ISO UTC (compatível com DynamoDB)."""
    return datetime.now(timezone.utc).strftime(ISO)


class ChatRepository:
    """
    Repositório responsável por gerenciar entidades relacionadas a Chats no DynamoDB.

    Estrutura principal (Single Table Design):
    - PK: USER#{user_id} | SK: CHAT#{chat_id} → dados do chat
    - PK: CHAT#{chat_id} | SK: MSG#{timestamp}#{message_id} → mensagens
    - PK: USER#{user_id} | SK: SESSION#{session_id} → sessões ativas e encerradas

    Índices Secundários (GSIs):
    - GSI1: listagem de chats por usuário
    - GSI2: rastreamento de sessões por status
    - GSI3: listagem de sessões por chat
    - GSI4: listagem de mensagens por usuário
    """

    def __init__(self, ddb):
        """
        Inicializa o repositório de chats.

        Args:
            ddb: Cliente DynamoDB configurado para operações de leitura e escrita.
        """
        self.db = ddb
        self.table = ddb.table()

    def create_chat(self, user_id: str, title: str) -> Dict[str, Any]:
        chat_id = str(uuid.uuid4())
        ts = now_iso()

        item = {
            "PK": f"USER#{user_id}",
            "SK": f"CHAT#{chat_id}",
            "type": "CHAT",
            "data": {
                "chat_id": chat_id,
                "user_id": user_id,
                "title": title,
                "created_at": ts,
                "updated_at": ts,
                "last_message_preview": None,
                "locked": False,
            },
            "GSI1PK": f"USER#{user_id}",
            "GSI1SK": f"CHAT#{ts}#{chat_id}",
        }

        self.db.put(item)
        return item["data"]

    def get_chat(self, user_id: str, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera um chat específico de um usuário.

        Args:
            user_id: ID do usuário.
            chat_id: ID do chat.

        Returns:
            Dicionário com os dados do chat, ou None se não encontrado.
        """
        item = self.db.get(pk=f"USER#{user_id}", sk=f"CHAT#{chat_id}")
        return item.get("data") if item else None

    def list_chats(
        self, user_id: str, limit: int = 20, last_key: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Lista chats de um usuário, ordenados por data de criação (mais recentes primeiro).

        Args:
            user_id: ID do usuário.
            limit: Quantidade máxima de chats retornados.
            last_key: Ponto de paginação para consultas contínuas.

        Returns:
            Dicionário com lista de chats e chave de continuação (`last_evaluated_key`).
        """
        params = {
            "IndexName": "GSI1",
            "KeyConditionExpression": Key("GSI1PK").eq(f"USER#{user_id}"),
            "ScanIndexForward": False,
            "Limit": limit,
        }
        if last_key:
            params["ExclusiveStartKey"] = last_key

        res = self.db.query(**params)
        items = res.get("Items", [])
        return {
            "items": [i["data"] for i in items],
            "last_evaluated_key": res.get("LastEvaluatedKey"),
        }

    def list_sessions_by_chat(
        self, chat_id: str, limit: int = 50, last_key: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Lista sessões associadas a um chat específico.

        Args:
            chat_id: ID do chat.
            limit: Limite de resultados.
            last_key: Paginação opcional.

        Returns:
            Dicionário com lista de sessões e chave de continuação.
        """
        params = {
            "IndexName": "GSI3",
            "KeyConditionExpression": Key("GSI3PK").eq(f"CHAT#{chat_id}"),
            "ScanIndexForward": False,
            "Limit": limit,
        }
        if last_key:
            params["ExclusiveStartKey"] = last_key

        res = self.db.query(**params)
        return {
            "items": [i["data"] for i in res.get("Items", [])],
            "last_evaluated_key": res.get("LastEvaluatedKey"),
        }

    def list_active_sessions_by_chat(self, chat_id: str) -> Dict[str, Any]:
        """
        Lista apenas as sessões ativas de um determinado chat.

        Args:
            chat_id: ID do chat.

        Returns:
            Dicionário contendo apenas sessões com status "active".
        """
        params = {
            "IndexName": "GSI3",
            "KeyConditionExpression": Key("GSI3PK").eq(f"CHAT#{chat_id}")
            & Key("GSI3SK").begins_with("SESSION#active#"),
        }

        res = self.db.query(**params)
        return {"items": [i["data"] for i in res.get("Items", [])]}

    def start_session(self, user_id: str, chat_id: str) -> Dict[str, Any]:
        """
        Inicia uma nova sessão de chat para um usuário.

        Args:
            user_id: ID do usuário.
            chat_id: ID do chat.

        Returns:
            Dicionário contendo os dados da sessão criada.
        """
        session_id = str(uuid.uuid4())
        ts = now_iso()

        item = {
            "PK": f"USER#{user_id}",
            "SK": f"SESSION#{session_id}",
            "type": "SESSION",
            "data": {
                "session_id": session_id,
                "chat_id": chat_id,
                "user_id": user_id,
                "status": "active",
                "started_at": ts,
                "last_event_at": ts,
                "ended_at": None,
            },
            "GSI2PK": "SESSION#STATUS#active",
            "GSI2SK": f"USER#{user_id}#START#{ts}#SESSION#{session_id}",
            "GSI3PK": f"CHAT#{chat_id}",
            "GSI3SK": f"SESSION#active#START#{ts}#SESSION#{session_id}",
        }

        self.db.put(item)
        return item["data"]

    def touch_session(self, user_id: str, session_id: str):
        """
        Atualiza o timestamp de última atividade da sessão.

        Args:
            user_id: ID do usuário.
            session_id: ID da sessão.
        """
        ts = now_iso()
        key = {"PK": f"USER#{user_id}", "SK": f"SESSION#{session_id}"}
        update_expr = "SET #data.#last_event_at = :t"
        vals = {":t": ts}
        names = {"#data": "data", "#last_event_at": "last_event_at"}
        try:
            self.db.update(
                key, update_expr, vals, names, condition="attribute_exists(PK)"
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ValueError(
                    f"Sessão {session_id} não encontrada para o usuário {user_id}"
                )
            raise

    def end_session(self, user_id: str, session_id: str):
        """
        Encerra uma sessão, alterando o status e movendo-a de GSI ativo para encerrado.

        Args:
            user_id: ID do usuário.
            session_id: ID da sessão.
        """
        ts = now_iso()
        key = {"PK": f"USER#{user_id}", "SK": f"SESSION#{session_id}"}
        update_expr = (
            "SET #data.#status = :e, #data.#ended_at = :t, GSI2PK = :p2, GSI3SK = :g3"
        )
        vals = {
            ":e": "ended",
            ":t": ts,
            ":p2": "SESSION#STATUS#ended",
            ":g3": f"SESSION#ended#START#{ts}#SESSION#{session_id}",
        }
        names = {"#data": "data", "#status": "status", "#ended_at": "ended_at"}
        try:
            self.db.update(
                key, update_expr, vals, names, condition="attribute_exists(PK)"
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return
            raise

    def append_message(
        self,
        chat_id: str,
        user_id: str,
        role: str,
        content: str,
        ttl: int = 0,
        msg_id=None,
    ) -> Dict[str, Any]:
        """
        Insere uma nova mensagem no histórico do chat.

        Args:
            chat_id: ID do chat.
            user_id: ID do usuário remetente.
            role: Papel da mensagem ("user" ou "ai").
            content: Texto da mensagem.
            ttl: Tempo de expiração opcional (em segundos).

        Returns:
            Dicionário com os dados da mensagem criada.
        """
        if msg_id is None:
            msg_id = str(uuid.uuid4())

        ts = now_iso()

        item = {
            "PK": f"CHAT#{chat_id}",
            "SK": f"MSG#{ts}#{msg_id}",
            "type": "MSG",
            "data": {
                "message_id": msg_id,
                "chat_id": chat_id,
                "user_id": user_id,
                "role": role,
                "content": content,
                "created_at": ts,
            },
            "GSI4PK": f"USER#{user_id}#MSG",
            "GSI4SK": f"MSG#{ts}#{chat_id}#{msg_id}",
        }
        if ttl:
            item["ttl"] = ttl

        self.db.put(item)
        return item["data"]

    def get_messages(
        self, chat_id: str, limit: int = 100, last_key: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Retorna mensagens de um chat, ordenadas cronologicamente.

        Args:
            chat_id: ID do chat.
            limit: Limite de mensagens.
            last_key: Paginação opcional.

        Returns:
            Dicionário com lista de mensagens e `last_evaluated_key`.
        """
        params = {
            "KeyConditionExpression": Key("PK").eq(f"CHAT#{chat_id}")
            & Key("SK").begins_with("MSG#"),
            "ScanIndexForward": True,
            "Limit": limit,
        }
        if last_key:
            params["ExclusiveStartKey"] = last_key

        res = self.db.query(**params)
        return {
            "items": [i["data"] for i in res.get("Items", [])],
            "last_evaluated_key": res.get("LastEvaluatedKey"),
        }

    def update_chat_preview_and_ts(self, user_id: str, chat_id: str, preview: str):
        """
        Atualiza o preview e timestamp de um chat após nova mensagem.

        Args:
            user_id: ID do usuário.
            chat_id: ID do chat.
            preview: Texto resumido da última mensagem.
        """
        ts = now_iso()
        key = {"PK": f"USER#{user_id}", "SK": f"CHAT#{chat_id}"}
        update_expr = (
            "SET #data.#updated_at = :u, #data.#last_message_preview = :p, GSI1SK = :g1"
        )
        vals = {":u": ts, ":p": preview, ":g1": f"CHAT#{ts}#{chat_id}"}
        names = {
            "#data": "data",
            "#updated_at": "updated_at",
            "#last_message_preview": "last_message_preview",
        }
        try:
            # Garante que o item exista; evita criação implícita e erro de path
            self.db.update(
                key, update_expr, vals, names, condition="attribute_exists(PK)"
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ValueError(
                    f"Chat {chat_id} não encontrado para o usuário {user_id}"
                )
            raise

    def update_chat_title(self, user_id: str, chat_id: str, new_title: str):
        """
        Atualiza o título de um chat existente.

        Args:
            user_id: ID do usuário.
            chat_id: ID do chat.
            new_title: Novo título a ser atribuído.
        """
        ts = now_iso()
        key = {"PK": f"USER#{user_id}", "SK": f"CHAT#{chat_id}"}
        update_expr = "SET #data.#title = :t, #data.#updated_at = :u, GSI1SK = :g1"
        vals = {":t": new_title, ":u": ts, ":g1": f"CHAT#{ts}#{chat_id}"}
        names = {
            "#data": "data",
            "#title": "title",
            "#updated_at": "updated_at",
        }
        try:
            self.db.update(
                key, update_expr, vals, names, condition="attribute_exists(PK)"
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ValueError(
                    f"Chat {chat_id} não encontrado para o usuário {user_id}"
                )
            raise

    def save_feedback(
        self, user_id: str, chat_id: str, rating: int, comment: Optional[str] = None
    ):
        """
        Salva o feedback do usuário em um chat e bloqueia novas mensagens.
        Atualiza o mapa 'data' inteiro para evitar erros de path no DynamoDB.
        """
        ts = now_iso()

        chat_data = self.get_chat(user_id=user_id, chat_id=chat_id)
        if not chat_data:
            raise ValueError(f"Chat {chat_id} não encontrado para o usuário {user_id}")

        if chat_data.get("locked") is True and chat_data.get("feedback"):
            raise ValueError("Este chat já foi encerrado e possui feedback registrado.")

        chat_data["feedback"] = {"rating": rating, "comment": comment, "created_at": ts}
        chat_data["locked"] = True
        chat_data["updated_at"] = ts

        key = {"PK": f"USER#{user_id}", "SK": f"CHAT#{chat_id}"}
        update_expr = "SET #data = :d"
        vals = {":d": chat_data}
        names = {"#data": "data"}

        self.db.update(key, update_expr, vals, names)

        return {
            "message": "Feedback salvo e chat bloqueado com sucesso.",
            "rating": rating,
            "comment": comment,
            "locked": True,
        }
