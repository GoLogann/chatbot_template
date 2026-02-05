"""
Módulo de prompts para o chatbot.

Este módulo centraliza todos os prompts do sistema, facilitando
a customização e manutenção do comportamento do chatbot.

Para customizar o comportamento do chatbot:
1. Edite o SYSTEM_PROMPT abaixo
2. Adicione novos prompts conforme necessário
3. Use as funções auxiliares para prompts dinâmicos
"""

# Prompt principal do sistema - customize conforme seu caso de uso
SYSTEM_PROMPT = """Você é um assistente virtual inteligente e prestativo.

**Seu objetivo:**
- Ajudar os usuários de forma clara, objetiva e amigável
- Responder perguntas com precisão e contexto relevante
- Manter um tom profissional mas acessível

**Diretrizes:**
- Seja conciso, mas completo nas respostas
- Se não souber algo, seja honesto e sugira alternativas
- Mantenha o contexto da conversa anterior
- Responda sempre no idioma do usuário

**Limitações:**
- Não forneça informações médicas, legais ou financeiras específicas
- Recomende consultar profissionais especializados quando apropriado
"""


def get_system_prompt() -> str:
    """
    Retorna o prompt do sistema.

    Customize esta função para adicionar lógica dinâmica ao prompt,
    como informações de contexto, hora atual, dados do usuário, etc.

    Returns:
        str: Prompt do sistema configurado
    """
    return SYSTEM_PROMPT


def get_custom_prompt(context: dict = None) -> str:
    """
    Gera um prompt customizado com contexto adicional.

    Args:
        context: Dicionário com informações de contexto
            - user_name: Nome do usuário
            - company: Nome da empresa
            - role: Papel/função do chatbot
            - additional_instructions: Instruções adicionais

    Returns:
        str: Prompt customizado

    Exemplo:
        prompt = get_custom_prompt({
            "user_name": "João",
            "company": "Empresa X",
            "role": "Assistente de vendas"
        })
    """
    if not context:
        return SYSTEM_PROMPT

    parts = [SYSTEM_PROMPT]

    if context.get("user_name"):
        parts.append(f"\n**Usuário:** {context['user_name']}")

    if context.get("company"):
        parts.append(f"\n**Empresa:** {context['company']}")

    if context.get("role"):
        parts.append(f"\n**Seu papel:** {context['role']}")

    if context.get("additional_instructions"):
        parts.append(f"\n**Instruções adicionais:**\n{context['additional_instructions']}")

    return "\n".join(parts)
