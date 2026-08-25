from pydantic import BaseModel


class InterestInput(BaseModel):
    words_in_title: dict[str, int] = {}
    words_in_description: dict[str, int] = {}
