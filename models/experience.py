from enum import Enum


class Experience(Enum):
    JUNIOR = "Junior"
    MID_LEVEL = "Mid-Level"
    EXPERIENCED = "Experienced"
    SENIOR = "Senior"

    @classmethod
    def from_years_required(cls, years_required: int) -> "Experience":
        if years_required <= 2:
            return Experience.JUNIOR
        elif 3 <= years_required <= 5:
            return Experience.MID_LEVEL
        elif 6 <= years_required <= 9:
            return Experience.EXPERIENCED
        else:
            return Experience.SENIOR

    @classmethod
    def from_str(cls, experience: str) -> "Experience | None":
        for value in Experience:
            if experience == str(value):
                return value
        return None

    def __str__(self):
        return str(self.value)
