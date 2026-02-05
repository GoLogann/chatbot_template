import logging

from langchain_aws import ChatBedrockConverse
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.core.config import Settings
from app.core.service.llm.base_langchain_service import BaseLangChainService

logger = logging.getLogger(__name__)


class BedrockChatService(BaseLangChainService):
    """
    Serviço responsável por integrar o modelo de chat da Amazon Bedrock
    (ChatBedrockConverse) com a aplicação.

    Atua como um wrapper simplificado sobre o LLM, permitindo criação de
    prompts e acesso centralizado ao modelo configurado.
    """

    def __init__(self, settings: Settings, repo, bedrock_client):
        """
        Inicializa o serviço de chat Bedrock.

        Args:
            settings: Configurações globais da aplicação (credenciais, modelo, região, etc.).
            repo: Repositório de mensagens persistidas (histórico de chat).
            bedrock_client: Cliente AWS Bedrock já autenticado.
        """
        super().__init__(repo)
        self.settings = settings
        self.bedrock_client = bedrock_client

    def get_llm(self):
        """
        Retorna a instância do modelo LLM configurado na AWS Bedrock.

        Returns:
            Instância de ChatBedrockConverse pronta para uso.

        Raises:
            Exception: Se houver falha na inicialização do modelo (ex.: credenciais incorretas).
        """
        try:
            return ChatBedrockConverse(
                credentials_profile_name=self.settings.AWS_PROFILE,
                model_id=self.settings.BEDROCK_MODEL_ID_CHAT,
                region_name=self.settings.AWS_REGION,
                temperature=self.settings.TEMPERATURE,
            )
        except Exception as e:
            logger.error(f"Falha ao inicializar LLM Bedrock: {e}")
            raise

    def create_prompt(self) -> ChatPromptTemplate:
        """
        Cria o template base de prompt usado nas conversas com o LLM.

        O template define o comportamento do assistente e estrutura o histórico
        de mensagens para manter contexto durante o diálogo.

        Returns:
            ChatPromptTemplate configurado com mensagens de sistema, histórico e input humano.
        """
        return ChatPromptTemplate.from_messages([
            ("system", "Você é um assistente de IA prestativo."),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ])
