"""
Registry para gerenciamento de ferramentas do chatbot.

O ToolRegistry permite:
- Registrar ferramentas de forma centralizada
- Habilitar/desabilitar ferramentas dinamicamente
- Obter lista de ferramentas para uso com LangChain/LangGraph
"""

import logging
from typing import Callable, Dict, List, Optional

from langchain_core.tools import BaseTool, StructuredTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry centralizado para ferramentas do chatbot.

    Exemplo de uso:
        registry = ToolRegistry()

        # Registrar uma função como ferramenta
        @tool
        def buscar_produto(nome: str) -> str:
            '''Busca um produto pelo nome.'''
            return f"Produto: {nome}"

        registry.register(buscar_produto)

        # Ou registrar diretamente
        registry.register_function(
            func=minha_funcao,
            name="minha_ferramenta",
            description="Descrição para o LLM"
        )

        # Obter ferramentas para o LLM
        tools = registry.get_tools()
    """

    def __init__(self):
        """Inicializa o registry vazio."""
        self._tools: Dict[str, BaseTool] = {}
        self._enabled: Dict[str, bool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        Registra uma ferramenta no registry.

        Args:
            tool: Ferramenta LangChain (criada com @tool ou StructuredTool)
        """
        name = tool.name
        self._tools[name] = tool
        self._enabled[name] = True
        logger.info(f"[ToolRegistry] Ferramenta registrada: {name}")

    def register_function(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        Registra uma função Python como ferramenta.

        Args:
            func: Função a ser registrada
            name: Nome da ferramenta (default: nome da função)
            description: Descrição para o LLM (default: docstring da função)
        """
        tool = StructuredTool.from_function(
            func=func,
            name=name or func.__name__,
            description=description or func.__doc__ or "Sem descrição",
        )
        self.register(tool)

    def unregister(self, name: str) -> bool:
        """
        Remove uma ferramenta do registry.

        Args:
            name: Nome da ferramenta

        Returns:
            True se removida, False se não existia
        """
        if name in self._tools:
            del self._tools[name]
            del self._enabled[name]
            logger.info(f"[ToolRegistry] Ferramenta removida: {name}")
            return True
        return False

    def enable(self, name: str) -> bool:
        """
        Habilita uma ferramenta.

        Args:
            name: Nome da ferramenta

        Returns:
            True se habilitada, False se não existe
        """
        if name in self._tools:
            self._enabled[name] = True
            logger.info(f"[ToolRegistry] Ferramenta habilitada: {name}")
            return True
        return False

    def disable(self, name: str) -> bool:
        """
        Desabilita uma ferramenta (não será retornada em get_tools).

        Args:
            name: Nome da ferramenta

        Returns:
            True se desabilitada, False se não existe
        """
        if name in self._tools:
            self._enabled[name] = False
            logger.info(f"[ToolRegistry] Ferramenta desabilitada: {name}")
            return True
        return False

    def get_tools(self, include_disabled: bool = False) -> List[BaseTool]:
        """
        Retorna lista de ferramentas registradas.

        Args:
            include_disabled: Se True, inclui ferramentas desabilitadas

        Returns:
            Lista de ferramentas para uso com LangChain
        """
        if include_disabled:
            return list(self._tools.values())

        return [
            tool for name, tool in self._tools.items()
            if self._enabled.get(name, True)
        ]

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Retorna uma ferramenta específica.

        Args:
            name: Nome da ferramenta

        Returns:
            Ferramenta ou None se não existe
        """
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, any]]:
        """
        Lista todas as ferramentas com seus status.

        Returns:
            Lista de dicts com name, description, enabled
        """
        return [
            {
                "name": name,
                "description": tool.description,
                "enabled": self._enabled.get(name, True),
            }
            for name, tool in self._tools.items()
        ]

    def clear(self) -> None:
        """Remove todas as ferramentas do registry."""
        self._tools.clear()
        self._enabled.clear()
        logger.info("[ToolRegistry] Todas as ferramentas removidas")

    def __len__(self) -> int:
        """Retorna número de ferramentas registradas."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Verifica se uma ferramenta está registrada."""
        return name in self._tools
