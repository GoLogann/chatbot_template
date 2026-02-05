from __future__ import annotations

from typing import Any, Dict, List

import boto3
from langchain_aws import BedrockEmbeddings, ChatBedrock

from app.core.config import Settings


class BedrockClient:
    """Cliente para geração (chat) e embeddings no Bedrock."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        # session_kwargs: Dict[str, Any] = {"region_name": settings.AWS_REGION}
        # if settings.AWS_PROFILE:
        #     session_kwargs["profile_name"] = settings.AWS_PROFILE

        # session = boto3.Session(**session_kwargs)


        self.llm = ChatBedrock(
            model_id=settings.BEDROCK_MODEL_ID_CHAT,
            region_name=self.settings.AWS_REGION,
            temperature=self.settings.TEMPERATURE,
        )
        self.emb = BedrockEmbeddings(
            model_id=settings.BEDROCK_MODEL_ID_EMBED,
            credentials_profile_name=settings.AWS_PROFILE,
            region_name=self.settings.AWS_REGION,
        )

    def chat(self, prompt: str) -> str:
        resp = self.llm.invoke(prompt)
        return resp.content if hasattr(resp, "content") else str(resp)

    def embed(self, text: str) -> List[float]:
        return self.emb.embed_query(text)
