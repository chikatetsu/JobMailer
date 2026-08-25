from enum import Enum

from pydantic import BaseModel


class SalaryPeriod(Enum):
    YEARLY = "yearly"
    MONTHLY = "monthly"
    DAILY = "daily"
    HOURLY = "hourly"

    @classmethod
    def from_string(cls, pay_period: str):
        interval_mapping = {
            "ANNUAL": cls.YEARLY,
            "YEAR": cls.YEARLY,
            "MONTH": cls.MONTHLY,
            "DAY": cls.DAILY,
            "HOUR": cls.HOURLY,
        }
        if pay_period in interval_mapping:
            return interval_mapping[pay_period].value
        elif pay_period in cls.__members__:
            return cls[pay_period].value
        else:
            raise ValueError(f"Unsupported compensation interval: {pay_period}")


class Salary(BaseModel):
    min_amount: int
    max_amount: int
    currency: str = "€"

    @staticmethod
    def from_raw(min_amount: int | float, max_amount: int | float, period: SalaryPeriod, currency: str = "€"):
        if period == SalaryPeriod.MONTHLY:
            return Salary(min_amount=int(min_amount * 12), max_amount=int(max_amount * 12), currency=currency)
        elif period == SalaryPeriod.DAILY:
            return Salary(min_amount=int(min_amount * 260), max_amount=int(max_amount * 260), currency=currency)
        elif period == SalaryPeriod.HOURLY:
            return Salary(min_amount=int(min_amount * 1820), max_amount=int(max_amount * 1820), currency=currency)
        else:
            return Salary(min_amount=int(min_amount), max_amount=int(max_amount), currency=currency)

    def __str__(self) -> str:
        return f"{self.min_amount} - {self.max_amount} {self.currency}"
