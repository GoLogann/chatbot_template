"""
Ferramentas de exemplo para o chatbot.

Este arquivo contém exemplos de ferramentas que podem ser usadas
como referência para criar suas próprias ferramentas.

IMPORTANTE: Estas ferramentas são apenas exemplos e estão
desabilitadas por padrão. Para usá-las, registre-as no registry.

Exemplo de uso:
    from app.core.tool import ToolRegistry
    from app.core.tool.examples import get_example_tools

    registry = ToolRegistry()
    for tool in get_example_tools():
        registry.register(tool)
"""

from datetime import datetime
from typing import Optional

from langchain_core.tools import tool


@tool
def get_current_datetime() -> str:
    """
    Retorna a data e hora atual.

    Use esta ferramenta quando o usuário perguntar sobre:
    - Que horas são
    - Qual é a data de hoje
    - Data e hora atual
    """
    now = datetime.now()
    return now.strftime("%d/%m/%Y às %H:%M:%S")


@tool
def calculate(expression: str) -> str:
    """
    Realiza cálculos matemáticos simples.

    Use esta ferramenta para:
    - Somar, subtrair, multiplicar ou dividir números
    - Calcular porcentagens
    - Operações matemáticas básicas

    Args:
        expression: Expressão matemática (ex: "2 + 2", "10 * 5", "100 / 4")

    Retorna o resultado do cálculo.
    """
    try:
        # ATENÇÃO: eval é perigoso! Em produção, use uma biblioteca segura
        # como `numexpr` ou implemente um parser próprio
        allowed_chars = set("0123456789+-*/().% ")
        if not all(c in allowed_chars for c in expression):
            return "Erro: Expressão contém caracteres não permitidos"

        result = eval(expression)
        return f"Resultado: {result}"
    except Exception as e:
        return f"Erro ao calcular: {str(e)}"


@tool
def search_knowledge_base(query: str, category: Optional[str] = None) -> str:
    """
    Busca informações na base de conhecimento.

    Use esta ferramenta quando precisar buscar:
    - Informações sobre produtos
    - Políticas da empresa
    - FAQs e documentação
    - Procedimentos internos

    Args:
        query: Termo de busca
        category: Categoria opcional (produtos, politicas, faq)

    Retorna informações relevantes encontradas.
    """
    # EXEMPLO: Em produção, substitua por uma busca real
    # (banco de dados, Elasticsearch, vector store, etc.)

    mock_data = {
        "produtos": {
            "preço": "Nossos preços variam de R$50 a R$500 dependendo do produto.",
            "entrega": "Entregamos em todo o Brasil em até 10 dias úteis.",
            "garantia": "Todos os produtos têm garantia de 12 meses.",
        },
        "politicas": {
            "troca": "Trocas podem ser feitas em até 30 dias após a compra.",
            "reembolso": "Reembolsos são processados em até 5 dias úteis.",
            "privacidade": "Seus dados são protegidos conforme a LGPD.",
        },
        "faq": {
            "horario": "Atendemos de segunda a sexta, das 9h às 18h.",
            "contato": "Você pode nos contatar pelo email suporte@empresa.com",
            "pagamento": "Aceitamos cartão, boleto e PIX.",
        },
    }

    results = []

    # Busca em todas as categorias ou na específica
    categories_to_search = [category] if category else mock_data.keys()

    for cat in categories_to_search:
        if cat in mock_data:
            for key, value in mock_data[cat].items():
                if query.lower() in key.lower() or query.lower() in value.lower():
                    results.append(f"[{cat.upper()}] {value}")

    if results:
        return "\n".join(results)
    else:
        return f"Nenhuma informação encontrada para: {query}"


def get_example_tools():
    """
    Retorna lista de ferramentas de exemplo.

    Returns:
        Lista de ferramentas prontas para registro
    """
    return [
        get_current_datetime,
        calculate,
        search_knowledge_base,
    ]
