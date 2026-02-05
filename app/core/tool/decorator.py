from langchain_core.tools import tool as langchain_tool

# Re-exporta o decorator do LangChain para manter compatibilidade
# e permitir customizações futuras
tool = langchain_tool
