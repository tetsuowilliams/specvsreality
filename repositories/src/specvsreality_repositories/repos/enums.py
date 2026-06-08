from enum import Enum

from specvsreality_repositories.models.enums import SpecItemImportance, SpecItemType

__all__ = ["VersionStatus", "SpecItemImportance", "SpecItemType"]


class VersionStatus(Enum):
    ACTIVE = "active"
    UPDATED = "updated"
    INACTIVE = "inactive"
    DELETED = "deleted"
