from dependency_injector import containers, providers

from app.core.config import Settings
from infra.bedrock.bedrock_client import BedrockClient
from infra.dynamodb.dynamodb_client import DynamoDBClient
from infra.tracing.tracing_client import TracerService


class Gateways(containers.DeclarativeContainer):
    """
    Container para clientes de infraestrutura (gateways).

    Inclui:
    - bedrock_client: Cliente AWS Bedrock para LLM
    - dynamodb_client: Cliente AWS DynamoDB para persistência
    - tracer_service: Serviço de tracing Langfuse
    """

    settings = providers.Dependency(instance_of=Settings)

    bedrock_client = providers.Singleton(
        BedrockClient,
        settings=settings
    )

    dynamodb_client = providers.Singleton(
        DynamoDBClient,
        settings=settings
    )

    tracer_service = providers.Singleton(
        TracerService,
        settings=settings
    )
