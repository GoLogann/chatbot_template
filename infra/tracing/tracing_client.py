from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from langfuse import Langfuse, observe
from langfuse.langchain import CallbackHandler

from app.core.config import Settings

logger = logging.getLogger(__name__)


class TracerService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.enabled = all([
            settings.LANGFUSE_HOST,
            settings.LANGFUSE_PUBLIC_KEY,
            settings.LANGFUSE_SECRET_KEY,
        ])

        if self.enabled:
            try:
                self.client = Langfuse(
                    host=settings.LANGFUSE_HOST,
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                )
                logger.info("[TracerService] Langfuse inicializado com sucesso.")
            except Exception as e:
                logger.error("[TracerService] Falha ao inicializar Langfuse: %s", e)
                self.enabled = False
        else:
            self.client = None
            logger.warning("[TracerService] Langfuse não habilitado (sem config).")

    def start_trace(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Cria um trace raiz (span principal).
        """
        if not self.enabled:
            return None
        return self.client.start_as_current_span(
            name=name,
            metadata=metadata or {}
        )

    def start_observation(
        self,
        as_type: str,
        name: str,
        input: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Cria uma observation genérica (retriever, tool, chain, etc).
        """
        if not self.enabled:
            return None
        return self.client.start_as_current_observation(
            as_type=as_type,
            name=name,
            input=input,
            metadata=metadata or {}
        )

    def start_generation(
        self,
        name: str,
        model: str,
        input: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Cria uma generation (usado em chamadas de LLM).
        """
        if not self.enabled:
            return None
        return self.client.start_as_current_generation(
            name=name,
            model=model,
            input=input,
            metadata=metadata or {}
        )

    def add_score(
        self,
        trace,
        name: str,
        value: float | int | str | bool,
        comment: Optional[str] = None,
    ):
        """Adiciona score de qualidade ou feedback ao trace."""
        if not self.enabled or not trace:
            return
        try:
            trace.score(
                name=name,
                value=value,
                comment=comment
            )
        except Exception as e:
            logger.error("[TracerService] Falha ao adicionar score: %s", e)

    def observe(self, as_type: str, name: Optional[str] = None) -> Callable:
        """Decorator para instrumentar funções automaticamente."""
        def wrapper(func):
            return observe(as_type=as_type, name=name or func.__name__)(func)
        return wrapper

    def get_langchain_handler(
        self,
        trace_name: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[CallbackHandler]:
        """
        Retorna um CallbackHandler configurado para LangChain/LangGraph.
        Use este handler no config do seu graph.
        
        Args:
            trace_name: Nome do trace no Langfuse
            user_id: ID do usuário (opcional)
            session_id: ID da sessão (opcional)
            tags: Tags para categorizar o trace (opcional)
            metadata: Metadados adicionais (opcional)
        
        Exemplo:
            handler = tracer.get_langchain_handler(
                trace_name="customer-support-agent",
                user_id="user_123",
                tags=["production", "support"]
            )
            result = graph.invoke(
                input={"messages": [HumanMessage(content="Hello")]},
                config={"callbacks": [handler]}
            )
        
        Returns:
            CallbackHandler ou None se tracing não estiver habilitado
        """
        if not self.enabled:
            return None
        
        try:
            return CallbackHandler(
                trace_name=trace_name,
                user_id=user_id,
                session_id=session_id,
                tags=tags,
                metadata=metadata,
            )
        except Exception as e:
            logger.error("[TracerService] Falha ao criar CallbackHandler: %s", e)
            return None

    def run_graph_with_tracing(
        self,
        graph,
        input_data: Dict[str, Any],
        trace_name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Executa um LangGraph compilado com tracing automático.
        
        Args:
            graph: LangGraph compilado (resultado de graph_builder.compile())
            input_data: Dados de entrada para o graph
            trace_name: Nome do trace
            user_id: ID do usuário (opcional)
            session_id: ID da sessão (opcional)
            tags: Tags para o trace (opcional)
            metadata: Metadados adicionais (opcional)
        
        Exemplo:
            result = tracer.run_graph_with_tracing(
                graph=my_compiled_graph,
                input_data={"messages": [HumanMessage(content="Hello")]},
                trace_name="customer-support-agent",
                user_id="user_123",
                tags=["production"],
                metadata={"environment": "prod", "version": "1.0"}
            )
        
        Returns:
            Resultado da execução do graph
        """
        handler = self.get_langchain_handler(
            trace_name=trace_name,
            user_id=user_id,
            session_id=session_id,
            tags=tags,
            metadata=metadata,
        )
        
        config = {"callbacks": [handler]} if handler else {}
        
        try:
            result = graph.invoke(input_data, config=config)
            logger.info(f"[TracerService] Graph '{trace_name}' executado com sucesso.")
            return result
        except Exception as e:
            logger.error(f"[TracerService] Erro ao executar graph '{trace_name}': %s", e)
            raise

    def trace_langgraph_agent(
        self,
        agent_name: str,
        input_data: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager para criar um trace customizado que envolve
        a execução do LangGraph com sub-tracing via CallbackHandler.
        
        Útil quando você precisa de controle total sobre o trace,
        como adicionar scores ou atualizar informações manualmente.
        
        Args:
            agent_name: Nome do agente/trace
            input_data: Dados de entrada
            metadata: Metadados adicionais (opcional)
        
        Exemplo:
            with tracer.trace_langgraph_agent(
                "email-classifier", 
                email_data,
                metadata={"priority": "high"}
            ) as ctx:
                handler = ctx["handler"]
                result = graph.invoke(
                    input={"email": email_data},
                    config={"callbacks": [handler]}
                )
                
                # Atualize o output manualmente
                ctx["span"].update(output=result)
                
                # Adicione scores
                ctx["span"].score_trace(
                    name="user-feedback",
                    value=1,
                    comment="Classificação correta"
                )
        
        Yields:
            Dict com 'handler' (CallbackHandler) e 'span' (Langfuse span)
        """
        if not self.enabled:
            yield {"handler": None, "span": None}
            return
        
        with self.client.start_as_current_span(
            name=agent_name,
            input=input_data,
            metadata=metadata or {}
        ) as span:
            handler = CallbackHandler()
            
            try:
                yield {
                    "handler": handler,
                    "span": span,
                }
            except Exception as e:
                logger.error(
                    f"[TracerService] Erro no trace '{agent_name}': %s", 
                    e
                )
                raise

    def flush(self):
        """
        Força o envio de todos os dados pendentes para o Langfuse.
        Útil no final de batch jobs ou testes.
        """
        if self.enabled and self.client:
            try:
                self.client.flush()
                logger.info("[TracerService] Flush executado com sucesso.")
            except Exception as e:
                logger.error("[TracerService] Erro ao executar flush: %s", e)
