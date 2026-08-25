from datetime import datetime

from pydantic import BaseModel

from inputs.interest_input import InterestInput
from models.candidate_status import CandidateStatus
from models.city import City
from models.contract_type import ContractType
from models.experience import Experience
from models.remote_type import RemoteType
from models.salary import Salary
from repositories import CompanyRepository
from utils.company_sorting import DevHiring


class JobReference:
    def __init__(self, job_id):
        self.id = job_id

class Job(BaseModel):
    id: str
    source: str
    title: str
    description: str
    company: str
    city: City
    address: str
    lat: float | None = None
    lon: float | None = None
    posted_date: datetime | None = None
    salary: Salary | None = None
    skills: list[str]
    experience: Experience
    remote_type: RemoteType
    contract_type: ContractType
    source_url: str
    real_url: str
    company_url: str
    company_logo: str
    company_id: int | None = None
    interest: int = 0
    is_seen: bool = False
    candidate_status: CandidateStatus = CandidateStatus.NOT_APPLIED
    candidate_date: datetime | None = None

    def get_interest(self, interest_input: InterestInput | None = None) -> int:
        if interest_input is None:
            return self.interest
        pts = 0
        formatted_title = self.title.replace(" ", "").replace("\n", "").replace("-", "").strip().lower()
        for word, weight in interest_input.words_in_title.items():
            if word in formatted_title:
                pts += weight
        full_description = self.title + self.description + "".join(self.skills)
        formatted_description = full_description.replace(" ", "").replace("\n", "").replace("-", "").strip().lower()
        for word, weight in interest_input.words_in_description.items():
            if word in formatted_description:
                pts += weight
        self.interest = pts
        return pts

    def get_company_infos(self, company_repo: CompanyRepository, do_commit: bool = True):
        company = company_repo.get_company_by_name(self.company, self.city)
        if company is not None:
            self.company_id = company.id
            self.company = company.name
            self.company_url = company.url
            self.company_logo = company.logo
            self.address = company.address
            self.lon = company.lon
            self.lat = company.lat
            company.dev_hiring = DevHiring.YES
            company_repo.update_company(company.id, company)
            if do_commit:
                company_repo.commit()

    def to_dict(self):
        dump = {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "description": self.description,
            "company": self.company,
            "city": self.city,
            "address": self.address,
            "lat": self.lat if self.lat else "",
            "lon": self.lon if self.lon else "",
            "posted_date": self.posted_date.strftime("%d/%m/%Y") if self.posted_date else "",
            "salary": str(self.salary) if self.salary else "",
            "skills": ", ".join(self.skills),
            "experience": str(self.experience),
            "remote_type": str(self.remote_type),
            "contract_type": str(self.contract_type),
            "source_url": self.source_url,
            "real_url": self.real_url,
            "company_url": self.company_url,
            "company_logo": self.company_logo,
            "company_id": self.company_id,
            "interest": self.interest,
            "is_seen": self.is_seen,
            "candidate_status": self.candidate_status,
            "candidate_date": self.candidate_date,
        }
        return dump
