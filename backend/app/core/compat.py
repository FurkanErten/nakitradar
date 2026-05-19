"""Python version compatibility helpers.

NakitRadar AI is intended to run on Python 3.10+.
Python 3.11 introduced enum.StrEnum. Some hackathon machines still ship with
Python 3.10, so we provide a small fallback that behaves like StrEnum for the
simple enum use cases in this project.
"""

try:  # pragma: no cover - depends on interpreter version
    from app.core.compat import StrEnum as _NativeStrEnum

    StrEnum = _NativeStrEnum
except ImportError:  # Python 3.10
    from enum import Enum

    class StrEnum(str, Enum):
        @staticmethod
        def _generate_next_value_(name, start, count, last_values):
            return name.lower()

        def __str__(self) -> str:
            return self.value
