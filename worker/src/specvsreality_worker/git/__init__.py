"""Git access layer: the only module that touches GitPython."""

from specvsreality_worker.git.git_client import GitClient, GitClientError, RefRecord

__all__ = ["GitClient", "GitClientError", "RefRecord"]
