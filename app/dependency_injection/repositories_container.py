from dependency_injector import containers, providers

from app.core.config import Settings
from infra.repositories.chat_repository import ChatRepository


class Repositories(containers.DeclarativeContainer):
    config = providers.Configuration()
    gateways = providers.DependenciesContainer()
    settings = providers.Dependency(instance_of=Settings)
    
    chat_repository = providers.Factory(
        ChatRepository,
        ddb=gateways.dynamodb_client
    )
