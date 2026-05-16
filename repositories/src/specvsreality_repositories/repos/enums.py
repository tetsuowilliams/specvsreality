from enum import Enum


class VersionStatus(Enum):
    ACTIVE = "active"
    UPDATED = "updated"
    INACTIVE = "inactive"
    DELETED = "deleted"
