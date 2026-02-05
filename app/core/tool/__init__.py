"""
Módulo de ferramentas (tools) para o chatbot.

Este módulo fornece uma estrutura para criar e gerenciar ferramentas
que o LLM pode usar durante a conversa.

Uso básico:
    from app.core.tool import ToolRegistry, tool

    # Criar uma ferramenta simples
    @tool
    def minha_ferramenta(parametro: str) -> str:
        '''Descrição da ferramenta para o LLM.'''
        return f"Resultado: {parametro}"

    # Registrar no registry
    registry = ToolRegistry()
    registry.register(minha_ferramenta)

    # Obter ferramentas para usar com LangChain
    tools = registry.get_tools()
"""

from app.core.tool.registry import ToolRegistry
from app.core.tool.decorator import tool

__all__ = ["ToolRegistry", "tool"]
