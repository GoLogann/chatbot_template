from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WhatsAppProfile(BaseModel):
    """Perfil do contato no WhatsApp."""
    name: str


class WhatsAppContact(BaseModel):
    """Informações do contato que enviou a mensagem."""
    profile: WhatsAppProfile
    wa_id: str = Field(..., description="Número do WhatsApp (ex: 5511999999999)")


class WhatsAppTextMessage(BaseModel):
    """Conteúdo de mensagem de texto."""
    body: str


class WhatsAppMessage(BaseModel):
    """Mensagem recebida do WhatsApp."""
    from_: str = Field(..., alias="from", description="Número que enviou a mensagem")
    id: str = Field(..., description="ID único da mensagem")
    timestamp: str = Field(..., description="Timestamp Unix da mensagem")
    type: str = Field(..., description="Tipo da mensagem (text, image, etc)")
    text: Optional[WhatsAppTextMessage] = None

    class Config:
        populate_by_name = True


class WhatsAppMetadata(BaseModel):
    """Metadados do número de telefone do negócio."""
    display_phone_number: str
    phone_number_id: str


class WhatsAppValue(BaseModel):
    """Valor do evento de webhook."""
    messaging_product: str
    metadata: WhatsAppMetadata
    contacts: Optional[List[WhatsAppContact]] = None
    messages: Optional[List[WhatsAppMessage]] = None


class WhatsAppChange(BaseModel):
    """Mudança/evento do webhook."""
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    """Entrada do webhook (pode conter múltiplas mudanças)."""
    id: str
    changes: List[WhatsAppChange]


class WhatsAppWebhookPayload(BaseModel):
    """
    Payload completo do webhook do WhatsApp.

    Estrutura típica:
    {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {...},
                    "contacts": [...],
                    "messages": [...]
                },
                "field": "messages"
            }]
        }]
    }
    """
    object: str
    entry: List[WhatsAppEntry]

    def get_messages(self) -> List[Dict[str, Any]]:
        """
        Extrai todas as mensagens do payload.

        Returns:
            Lista de dicts com:
            - phone: número do remetente
            - name: nome do contato
            - message_id: ID da mensagem
            - text: conteúdo da mensagem (se texto)
            - type: tipo da mensagem
        """
        messages = []
        for entry in self.entry:
            for change in entry.changes:
                if change.field != "messages":
                    continue

                value = change.value
                contacts_map = {}

                if value.contacts:
                    for contact in value.contacts:
                        contacts_map[contact.wa_id] = contact.profile.name

                if value.messages:
                    for msg in value.messages:
                        messages.append({
                            "phone": msg.from_,
                            "name": contacts_map.get(msg.from_, "Unknown"),
                            "message_id": msg.id,
                            "text": msg.text.body if msg.text else None,
                            "type": msg.type,
                            "timestamp": msg.timestamp,
                            "phone_number_id": value.metadata.phone_number_id,
                        })

        return messages


class SendTextMessage(BaseModel):
    """Requisição para enviar mensagem de texto."""
    to: str = Field(..., description="Número destino (formato: 5511999999999)")
    text: str = Field(..., description="Conteúdo da mensagem")


class SendTemplateMessage(BaseModel):
    """Requisição para enviar mensagem de template."""
    to: str = Field(..., description="Número destino")
    template_name: str = Field(..., description="Nome do template aprovado")
    language_code: str = Field(default="pt_BR", description="Código do idioma")
    components: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Componentes do template (header, body, buttons)"
    )


class WhatsAppSendResponse(BaseModel):
    """Resposta do envio de mensagem."""
    messaging_product: str
    contacts: List[Dict[str, str]]
    messages: List[Dict[str, str]]


class WhatsAppSession(BaseModel):
    """
    Sessão de conversa do WhatsApp.

    Usado para manter estado entre mensagens do mesmo usuário.
    """
    phone: str = Field(..., description="Número do WhatsApp do usuário")
    user_id: str = Field(..., description="ID interno do usuário")
    chat_id: Optional[str] = Field(None, description="ID do chat associado")
    session_id: Optional[str] = Field(None, description="ID da sessão ativa")
    last_activity: Optional[str] = Field(None, description="Timestamp da última atividade")
