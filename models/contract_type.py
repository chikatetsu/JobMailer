from enum import Enum


class ContractType(Enum):
    CDI = "CDI"
    CDD = "CDD"
    INTERIM = "Intérimaire"
    SEASON = "Saisonnier"
    OTHER = "Other"
    INTERNSHIP = "Alternance"

    def __str__(self):
        return self.value

    @classmethod
    def from_str(cls, contract_type: str) -> "ContractType":
        for value in ContractType:
            if contract_type == str(value):
                return value
        return ContractType.OTHER
