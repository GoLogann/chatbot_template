from dependency_injector import containers, providers

from app.core.config import Settings
from app.dependency_injection.core_container import Core
from app.dependency_injection.gateways_container import Gateways
from app.dependency_injection.repositories_container import Repositories
from app.dependency_injection.services_container import Services
from app.dependency_injection.whatsapp_container import WhatsApp


class Application(containers.DeclarativeContainer):
    """
    Container raiz da aplicação.

    Estrutura:
    - settings: Configurações globais
    - gateways: Clientes de infraestrutura (Bedrock, DynamoDB, Langfuse)
    - repositories: Camada de acesso a dados
    - services: Serviços de negócio (Chat, Orchestrator)
    - whatsapp: Serviços de integração WhatsApp
    """

    settings = providers.Singleton(Settings)

    gateways = providers.Container(
        Gateways,
        settings=settings,
    )

    repositories = providers.Container(
        Repositories,
        settings=settings,
        gateways=gateways,
    )

    services = providers.Container(
        Services,
        settings=settings,
        gateways=gateways,
        repositories=repositories,
    )

    whatsapp = providers.Container(
        WhatsApp,
        settings=settings,
        services=services,
        repositories=repositories,
    )
