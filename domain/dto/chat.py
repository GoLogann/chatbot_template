from typing import Optional

from pydantic import BaseModel, Field


class AskBody(BaseModel):
    """DTO para requisições de chat."""
    user_id: str = Field(..., description="ID do usuário")
    question: str = Field(..., description="Pergunta ou mensagem do usuário")
    chat_id: Optional[str] = Field(None, description="ID do chat (opcional, será criado se não fornecido)")
    session_id: Optional[str] = Field(None, description="ID da sessão (opcional, será criado se não fornecido)")
