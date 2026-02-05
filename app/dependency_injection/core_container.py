from dependency_injector import containers, providers

from app.core.config import Settings


class Core(containers.DeclarativeContainer):
    """Container vazio - reservado para uso futuro."""
    settings = providers.Dependency(instance_of=Settings)
