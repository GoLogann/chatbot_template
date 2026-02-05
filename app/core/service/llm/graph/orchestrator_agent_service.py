import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Literal, Optional

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.core.config import Settings
from app.core.service.llm.base_langchain_service import BaseLangChainService
from app.core.service.llm.bedrock_chat_service import BedrockChatService
from app.core.service.llm.graph.prompts import get_system_prompt
from app.core.service.llm.graph.state import AgentState
from app.core.tool import ToolRegistry
from infra.repositories.chat_repository import ChatRepository
from infra.tracing.tracing_client import TracerService

logger = logging.getLogger(__name__)


class OrchestratorAgentService(BaseLangChainService):
    """
    Serviço orquestrador baseado em LangGraph.

    Suporta dois modos de operação:

    1. **Sem ferramentas** (padrão):
       START -> process_message -> respond -> END

    2. **Com ferramentas**:
       START -> process_message -> agent <-> tools -> END

    Para habilitar ferramentas:
        from app.core.tool import ToolRegistry
        from app.core.tool.examples import get_example_tools

        registry = ToolRegistry()
        for tool in get_example_tools():
            registry.register(tool)

        orchestrator = OrchestratorAgentService(
            ...,
            tool_registry=registry,
        )
    """

    def __init__(
        self,
        settings: Settings,
        llm_service: BedrockChatService,
        repo: ChatRepository,
        tracer: Optional[TracerService] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        """
        Inicializa o serviço de orquestração.

        Args:
            settings: Configurações globais da aplicação.
            llm_service: Serviço de LLM (Bedrock Chat).
            repo: Repositório para persistência de mensagens.
            tracer: Serviço de tracing (Langfuse) - opcional.
            tool_registry: Registry de ferramentas - opcional.
        """
        super().__init__(repo)
        self.settings = settings
        self.llm_service = llm_service
        self.tracer = tracer
        self.tool_registry = tool_registry

        self.tools: List[BaseTool] = []
        if tool_registry:
            self.tools = tool_registry.get_tools()
            if self.tools:
                logger.info(f"[Orchestrator] {len(self.tools)} ferramentas carregadas")

        self.llm = self.llm_service.get_llm()
        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            self.llm_with_tools = None

        self.system_message = SystemMessage(content=get_system_prompt())
        self.agent_runnable = self._build_graph()

    def _build_graph(self) -> Runnable:
        """
        Constrói o grafo de conversação.

        Se houver ferramentas registradas, cria um grafo com ciclo de ferramentas.
        Caso contrário, cria um grafo simples de pergunta-resposta.
        """
        logger.info("Compilando grafo do chatbot...")

        workflow = StateGraph(AgentState)

        if self.tools:
            # Grafo com suporte a ferramentas
            return self._build_graph_with_tools(workflow)
        else:
            # Grafo simples sem ferramentas
            return self._build_simple_graph(workflow)

    def _build_simple_graph(self, workflow: StateGraph) -> Runnable:
        """
        Constrói grafo simples: process_message -> respond -> END
        """
        workflow.add_node("process_message", self._process_message_node)
        workflow.add_node("respond", self._respond_node)

        workflow.set_entry_point("process_message")

        workflow.add_conditional_edges(
            "process_message",
            self._route_after_process,
            {
                "respond": "respond",
                "end": END,
            },
        )

        workflow.add_edge("respond", END)

        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    def _build_graph_with_tools(self, workflow: StateGraph) -> Runnable:
        """
        Constrói grafo com ferramentas: process_message -> agent <-> tools -> END

        O LLM pode decidir usar ferramentas ou responder diretamente.
        Se usar uma ferramenta, o resultado volta para o agente processar.
        """
        tool_node = ToolNode(self.tools)

        workflow.add_node("process_message", self._process_message_node)
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", tool_node)

        workflow.set_entry_point("process_message")

        workflow.add_conditional_edges(
            "process_message",
            self._route_after_process,
            {
                "respond": "agent",  # Vai para agent ao invés de respond
                "end": END,
            },
        )

        # Após o agente, verifica se precisa usar ferramentas
        workflow.add_conditional_edges(
            "agent",
            self._should_use_tools,
            {
                "tools": "tools",
                "end": END,
            },
        )

        # Após usar ferramentas, volta para o agente
        workflow.add_edge("tools", "agent")

        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    def _process_message_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Nó que processa a mensagem do usuário.

        Use este nó para:
        - Validar input
        - Extrair intenções
        - Preparar contexto adicional
        """
        logger.info("[PROCESS_MESSAGE] Processando mensagem do usuário...")

        messages = state.get("messages", [])

        if not messages:
            logger.warning("[PROCESS_MESSAGE] Nenhuma mensagem encontrada")
            return {"should_respond": False}

        user_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
        if not user_messages:
            logger.warning("[PROCESS_MESSAGE] Nenhuma mensagem de usuário encontrada")
            return {"should_respond": False}

        last_message = user_messages[-1].content
        logger.info(f"[PROCESS_MESSAGE] Mensagem: {last_message[:100]}...")

        return {
            "should_respond": True,
            "processed_input": last_message,
        }

    def _respond_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Nó que gera resposta (usado quando NÃO há ferramentas).
        """
        messages = state.get("messages", [])
        prompt_messages = [self.system_message] + messages

        callbacks = self._get_callbacks(state)

        try:
            if callbacks:
                response = self.llm.invoke(prompt_messages, config={"callbacks": callbacks})
            else:
                response = self.llm.invoke(prompt_messages)

            content = response.content.strip()
            return {"messages": [AIMessage(content=content)]}

        except Exception as e:
            logger.error(f"[RESPOND] Erro: {e}")
            return {"messages": [AIMessage(
                content="Desculpe, ocorreu um erro. Por favor, tente novamente."
            )]}

    def _agent_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Nó do agente (usado quando HÁ ferramentas).

        O LLM pode:
        1. Responder diretamente
        2. Chamar uma ou mais ferramentas
        """
        messages = state.get("messages", [])
        prompt_messages = [self.system_message] + messages

        callbacks = self._get_callbacks(state)

        try:
            if callbacks:
                response = self.llm_with_tools.invoke(
                    prompt_messages, config={"callbacks": callbacks}
                )
            else:
                response = self.llm_with_tools.invoke(prompt_messages)

            return {"messages": [response]}

        except Exception as e:
            logger.error(f"[AGENT] Erro: {e}")
            return {"messages": [AIMessage(
                content="Desculpe, ocorreu um erro. Por favor, tente novamente."
            )]}

    def _should_use_tools(self, state: AgentState) -> Literal["tools", "end"]:
        """
        Verifica se a última mensagem do agente contém chamadas de ferramenta.
        """
        messages = state.get("messages", [])
        if not messages:
            return "end"

        last_message = messages[-1]

        # Verifica se é uma AIMessage com tool_calls
        if isinstance(last_message, AIMessage):
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                logger.info(f"[ROUTE] Usando ferramentas: {[tc['name'] for tc in last_message.tool_calls]}")
                return "tools"

        return "end"

    def _route_after_process(
        self, state: AgentState
    ) -> Literal["respond", "end"]:
        """Roteamento após processamento da mensagem."""
        should_respond = state.get("should_respond", True)
        return "respond" if should_respond else "end"

    def _get_callbacks(self, state: AgentState) -> List:
        """Obtém callbacks para tracing (Langfuse)."""
        callbacks = []
        if self.tracer:
            handler = self.tracer.get_langchain_handler(
                trace_name="chatbot-response",
                user_id=state.get("user_id"),
                session_id=state.get("session_id"),
                metadata={
                    "chat_id": state.get("chat_id"),
                    "model": self.settings.BEDROCK_MODEL_ID_CHAT,
                    "tools_enabled": bool(self.tools),
                }
            )
            if handler:
                callbacks.append(handler)
        return callbacks

    async def execute_agent(
        self,
        user_id: str,
        prompt: str,
        chat_id: str,
        session_id: str,
        timeout: int = 120,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Executa o agente e transmite a resposta ao usuário.

        Args:
            user_id: ID do usuário
            prompt: Mensagem do usuário
            chat_id: ID do chat
            session_id: ID da sessão
            timeout: Tempo limite em segundos

        Yields:
            Eventos com tipo: agent_response, tool_call, tool_result, error, end
        """
        logger.info(f"Executando agente (chat={chat_id}, session={session_id})")

        history = self._get_session_history(chat_id).messages

        initial_state = {
            "messages": history + [HumanMessage(content=prompt)],
            "user_id": user_id,
            "chat_id": chat_id,
            "session_id": session_id,
        }
        config = {"configurable": {"thread_id": session_id}}

        full_response = ""
        stream_iterator = self.agent_runnable.astream(initial_state, config).__aiter__()

        try:
            while True:
                event = await asyncio.wait_for(
                    stream_iterator.__anext__(), timeout=timeout
                )

                for node_name, node_output in event.items():
                    if node_name == "__end__":
                        continue

                    if not node_output:
                        continue

                    messages = node_output.get("messages", [])
                    for msg in messages:
                        # Resposta do agente
                        if isinstance(msg, AIMessage):
                            content = getattr(msg, "content", None)
                            if isinstance(content, str) and content.strip():
                                full_response = content.strip()
                                yield {
                                    "type": "agent_response",
                                    "content": full_response,
                                }

                            # Notifica sobre chamadas de ferramenta
                            if hasattr(msg, "tool_calls") and msg.tool_calls:
                                for tc in msg.tool_calls:
                                    yield {
                                        "type": "tool_call",
                                        "tool": tc.get("name"),
                                        "args": tc.get("args"),
                                    }

                        # Resultado de ferramenta
                        elif isinstance(msg, ToolMessage):
                            yield {
                                "type": "tool_result",
                                "tool": msg.name,
                                "result": msg.content[:200] if msg.content else "",
                            }

        except StopAsyncIteration:
            logger.info("Execução concluída com sucesso.")

        except asyncio.TimeoutError:
            logger.error(f"Timeout após {timeout}s")
            yield {"type": "error", "message": f"Tempo limite de {timeout}s atingido"}

        except Exception as e:
            logger.exception("Erro na execução do agente.")
            yield {"type": "error", "message": str(e)}

        if self.tracer:
            self.tracer.flush()

        yield {
            "type": "end",
            "session_id": session_id,
            "chat_id": chat_id,
            "full_text": full_response,
        }

    def create_prompt(self, *args, **kwargs):
        """Método não utilizado neste agente."""
        raise NotImplementedError("Método não utilizado no agente LangGraph.")

    def get_llm(self, *args, **kwargs):
        """Retorna a instância do LLM configurado."""
        return self.llm_service.get_llm(*args, **kwargs)
