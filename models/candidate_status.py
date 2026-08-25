from enum import Enum


class CandidateStatus(Enum):
    NOT_APPLIED = "Not applied"
    WAITING_APPLICATION_RESPONSE = "Waiting Application Response"
    INTERVIEW = "Interview"
    WAITING_INTERVIEW_RESPONSE = "Waiting Interview Response"
    REJECTED = "Rejected"
    ACCEPTED = "Accepted"

    @classmethod
    def from_str(cls, candidate_status: str) -> "CandidateStatus | None":
        for value in CandidateStatus:
            if candidate_status == str(value):
                return value
        return None

    def __str__(self):
        return str(self.value)
