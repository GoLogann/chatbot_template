from dependency_injector import containers, providers

from app.core.config import Settings
from app.core.service.whatsapp.whatsapp_chat_service import WhatsAppChatService
from app.core.service.whatsapp.whatsapp_service import WhatsAppService


class WhatsApp(containers.DeclarativeContainer):
    """
    Container para serviços de integração WhatsApp.

    Inclui:
    - whatsapp_service: Envio de mensagens via Meta API
    - whatsapp_chat_service: Integração com ChatService
    """

    config = providers.Configuration()
    settings = providers.Dependency(instance_of=Settings)
    services = providers.DependenciesContainer()
    repositories = providers.DependenciesContainer()

    whatsapp_service = providers.Singleton(
        WhatsAppService,
        settings=settings
    )

    whatsapp_chat_service = providers.Factory(
        WhatsAppChatService,
        settings=settings,
        chat_service=services.chat_service,
        whatsapp_service=whatsapp_service,
        repo=repositories.chat_repository,
    )
