from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Estado do Agente para o LangGraph.

    Este estado é compartilhado entre todos os nós do grafo.
    Adicione novos campos conforme necessário para seu caso de uso.

    Campos base:
        messages: Histórico de mensagens da conversa
        user_id: ID do usuário
        chat_id: ID do chat
        session_id: ID da sessão

    Campos de controle:
        should_respond: Flag indicando se deve gerar resposta
        processed_input: Input processado/normalizado

    Campos customizáveis:
        context: Contexto adicional para o LLM
        metadata: Metadados da sessão
        custom_data: Dados customizados do seu caso de uso
    """

    # Campos base (obrigatórios)
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: Optional[str]
    chat_id: Optional[str]
    session_id: Optional[str]

    # Campos de controle do fluxo
    should_respond: Optional[bool]
    processed_input: Optional[str]

    # Campos customizáveis - adicione os seus aqui
    context: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    custom_data: Optional[Dict[str, Any]]
