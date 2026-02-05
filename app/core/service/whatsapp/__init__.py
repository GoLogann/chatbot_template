"""
Módulo de integração com WhatsApp.

Inclui:
- WhatsAppService: Envio de mensagens via Meta Cloud API
- WhatsAppChatService: Integração com ChatService para processamento de conversas
"""

from app.core.service.whatsapp.whatsapp_chat_service import WhatsAppChatService
from app.core.service.whatsapp.whatsapp_service import WhatsAppService

__all__ = ["WhatsAppService", "WhatsAppChatService"]
