from enum import Enum


class SecurityLevel(Enum):
    HIGH = 0
    LOW = 1

    @staticmethod
    def list():
        return list(map(lambda s: s.name, SecurityLevel))
