from enum import Enum
from typing import Self


class FormatType(Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    PLAIN = "plain"

    @classmethod
    def from_string(cls, format_type: str) -> Self:
        """Convert a string to the corresponding FormatType enum."""
        format_type_str = format_type.strip().lower()
        for format_type in cls:
            if format_type_str == format_type:
                return format_type
        raise ValueError(
            f"Invalid format type for description : '{format_type_str}'. Valid types are: {', '.join([description_format.value for description_format in cls])}"
        )
