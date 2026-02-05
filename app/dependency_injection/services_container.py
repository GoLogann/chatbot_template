from dependency_injector import containers, providers

from app.core.config import Settings
from app.core.service.chat.chat_service import ChatService
from app.core.service.llm.bedrock_chat_service import BedrockChatService
from app.core.service.llm.graph.orchestrator_agent_service import (
    OrchestratorAgentService,
)


class Services(containers.DeclarativeContainer):
    """
    Container para serviços de negócio.

    Inclui:
    - bedrock_chat_service: Serviço de integração com Bedrock
    - orchestrator_service: Serviço orquestrador LangGraph
    - chat_service: Serviço principal de chat
    """

    config = providers.Configuration()
    gateways = providers.DependenciesContainer()
    repositories = providers.DependenciesContainer()
    settings = providers.Dependency(instance_of=Settings)

    bedrock_chat_service = providers.Factory(
        BedrockChatService,
        settings=settings,
        repo=repositories.chat_repository,
        bedrock_client=gateways.bedrock_client
    )

    orchestrator_service = providers.Factory(
        OrchestratorAgentService,
        settings=settings,
        llm_service=bedrock_chat_service,
        repo=repositories.chat_repository,
        tracer=gateways.tracer_service,
    )

    chat_service = providers.Factory(
        ChatService,
        llm_service=orchestrator_service,
        repo=repositories.chat_repository
    )
