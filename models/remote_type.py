from enum import Enum


class RemoteType(Enum):
    ON_SITE = "Fully On-site"
    HYBRID = "Hybrid"
    REMOTE = "Fully Remote"

    def __str__(self):
        return self.value

    @classmethod
    def from_str(cls, remote_type: str) -> "RemoteType":
        for value in RemoteType:
            if remote_type == str(value):
                return value
        return RemoteType.ON_SITE
