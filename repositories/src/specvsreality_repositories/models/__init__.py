"""ORM models."""

from specvsreality_repositories.models.base import Base
from specvsreality_repositories.models.git_repo import GitRepo

__all__ = ["Base", "GitRepo"]
