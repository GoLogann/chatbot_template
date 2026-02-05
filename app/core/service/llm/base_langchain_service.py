import logging
from abc import ABC, abstractmethod
from typing import Callable

from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.runnables.history import RunnableWithMessageHistory

logger = logging.getLogger(__name__)


class BaseLangChainService(ABC):
    """
    Classe base para serviços que integram LangChain com a aplicação.

    Responsável por padronizar acesso ao LLM, histórico de mensagens
    e estrutura de execução de fluxos (runnables).
    """

    def __init__(self, repo):
        """
        Inicializa o serviço base.

        Args:
            repo: Repositório responsável por persistir e recuperar mensagens de chat.
        """
        self.repo = repo

    @abstractmethod
    def get_llm(self):
        """
        Retorna a instância do modelo de linguagem (LLM) configurado.
        Deve ser implementado pelas classes filhas.
        """
        pass

    @abstractmethod
    def create_prompt(self, *args, **kwargs) -> ChatPromptTemplate:
        """
        Cria e retorna um prompt LangChain para o LLM.

        Args:
            *args, **kwargs: Parâmetros dinâmicos usados na criação do prompt.

        Returns:
            Instância de ChatPromptTemplate configurada.
        """
        pass

    def _get_session_history(self, chat_id: str) -> ChatMessageHistory:
        """
        Recupera o histórico completo de mensagens de uma sessão.

        Args:
            chat_id: Identificador único do chat.

        Returns:
            ChatMessageHistory contendo as mensagens anteriores (usuário e assistente).
        """
        hist = ChatMessageHistory()
        messages = self.repo.get_messages(chat_id=chat_id, limit=1000)["items"]

        for m in messages:
            hist.add_message({"role": m["role"], "content": m["content"]})

        return hist

    def _with_history(self, runnable: Runnable, chat_id: str) -> RunnableWithMessageHistory:
        """
        Vincula o histórico de conversas a um Runnable LangChain.

        Isso permite que o modelo tenha contexto das interações anteriores,
        mantendo coerência entre turnos da conversa.

        Args:
            runnable: Instância de Runnable (pipeline LangChain) a ser executada.
            chat_id: Identificador do chat associado à sessão.

        Returns:
            RunnableWithMessageHistory configurado para utilizar o histórico persistido.
        """
        def get_history_func(_: None) -> ChatMessageHistory:
            return self._get_session_history(chat_id)

        return RunnableWithMessageHistory(
            runnable,
            get_history_func,
            input_messages_key="input",   
            history_messages_key="history", 
        )
