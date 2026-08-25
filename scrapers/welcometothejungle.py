import json
import re
import sys
from datetime import datetime
from urllib import parse

from inputs.scraper_input import ScraperInput
from models.city import City
from models.contract_type import ContractType
from models.experience import Experience
from models.job import Job, JobReference
from models.job_response import JobResponse
from models.remote_type import RemoteType
from models.salary import Salary, SalaryPeriod
from scrapers.scraper import BaseScraper, SessionScraper


class WelcomeToTheJungle(BaseScraper, SessionScraper):
    def __init__(self, city: City, scraper_input: ScraperInput, seen_jobs: set[str] | None = None, proxies: list[str] | str | None = None, ca_cert: str | None = None):
        BaseScraper.__init__(self, city, scraper_input, "https://www.welcometothejungle.com", seen_jobs=seen_jobs)
        SessionScraper.__init__(self, proxies, ca_cert)

    def _build_url(self, page: int) -> str:
        url = (
            f"{self.base_url}/fr/pages/"
            f"emploi-{parse.quote(self.scraper_input.search_term.replace('é', 'e'))}-"
            f"{parse.quote(str(self.city))}-{self.city.value.postal}"
            f"?page={page}"
        )
        self.log.error(url)
        return url

    def scrape(self) -> JobResponse:
        job_response = []
        for page in range(1, sys.maxsize):
            self.log.info(f"scraping page {page}...")
            url = self._build_url(page)
            try:
                response = self.session.get(url)
                if response.text == "":
                    self.log.error(f"Page {page} is empty")
                    break

                match = re.search(r'window\.__INITIAL_DATA__\s*=\s*"(.+?)"\s*\n', response.text)
                if not match:
                    self.log.error(f"No jobs found on page {page}")
                    break
                raw = match.group(1)
                data = json.loads(json.loads(f'"{raw}"'))
                if len(data["queries"]) == 0:
                    self.log.error(f"No jobs found on page {page}")
                    break
                hits = data["queries"][1]["state"]["data"]["results"][0]["hits"]
    
                jobs = []
                for job_json in hits:
                    job = self.process_job(job_json)
                    if job is not None:
                        jobs.append(job)
                if not jobs or len(jobs) == 0:
                    break
                job_response.extend(jobs)
            except Exception as e:
                self.log.error(e)
        self.log.info("finished scrapping")
        return JobResponse(job_response)

    def process_job(self, job_json: dict) -> Job | JobReference:
        slug = job_json.get("slug", "")
        job_id = self.get_id(slug)
        if job_id in self.seen_jobs:
            return JobReference(job_id)

        organization = job_json.get("organization", {})
        title = self.get_title(job_json)
        job = Job(
            id=job_id,
            source=WelcomeToTheJungle.__name__,
            title=title,
            description=self.get_description(job_json),
            company=self.get_company(organization),
            city=self.city,
            address=self.get_address(job_json),
            posted_date=self.get_posted_date(job_json),
            salary=self.get_salary(job_json),
            skills=self.get_skills(),
            experience=self.get_experience(job_json, title),
            remote_type=self.get_remote_type(job_json),
            contract_type=self.get_contract_type(job_json, title),
            source_url=self.get_source_url(organization, slug),
            real_url=self.get_real_url(),
            company_url=self.get_company_url(),
            company_logo=self.get_company_logo(organization)
        )
        self.seen_jobs.add(job_id)
        return job

    def get_id(self, slug: str) -> str:
        job_id = f"wj_{slug}"
        return job_id

    def get_title(self, job_json: dict) -> str:
        title = job_json.get("name", "")
        return title

    def get_description(self, job_json: dict) -> str:
        summary = job_json.get("summary", "")
        missions = job_json.get("key_missions", [])
        benefits = job_json.get("benefits", [])
        return f"{summary} {" ".join(missions)} {". ".join(benefits)}".strip()

    def get_company(self, orga_raw: dict) -> str:
        if not orga_raw:
            return ""
        company = orga_raw.get("name", "")
        return company

    def get_address(self, job_json: dict) -> str:
        office_raw = job_json.get("offices", [{}])[0]
        if not office_raw:
            return ""
        city = office_raw.get("city", "").title()
        return city

    def get_posted_date(self, job_json: dict) -> datetime | None:
        posted_raw = job_json.get("published_at_date", "")
        if posted_raw == "":
            return None
        posted_date = datetime.strptime(posted_raw, "%Y-%m-%d")
        return posted_date

    def get_salary(self, job_json: dict) -> Salary | None:
        min_raw = job_json.get("salary_minimum", None)
        max_raw = job_json.get("salary_maximum", None)
        period_raw = job_json.get("salary_period", None)
        currency = job_json.get("salary_currency", None)
        if min_raw is None or max_raw is None or period_raw is None:
            return None
        period_map = {
            "yearly": SalaryPeriod.YEARLY,
            "monthly": SalaryPeriod.MONTHLY,
            "daily": SalaryPeriod.DAILY,
        }
        period = period_map.get(period_raw, None)
        if period is None:
            print(f"period_raw: {period_raw}")
            return None
        if currency is not None:
            salary = Salary.from_raw(int(min_raw), int(max_raw), period, currency)
        else:
            salary = Salary.from_raw(int(min_raw), int(max_raw), period)
        return salary

    def get_skills(self) -> list[str]:
        # TODO
        return []

    def get_experience(self, job_json: dict, title) -> Experience:
        exp_raw = job_json.get("experience_level_minimum", None)
        if exp_raw is None:
            return BaseScraper.get_experience(self, title)
        experience = Experience.from_years_required(int(exp_raw))
        return experience

    def get_remote_type(self, job_json: dict) -> RemoteType:
        remote_map = {
            "partial": RemoteType.HYBRID,
            "unknown": RemoteType.ON_SITE,
        }
        remote_raw = job_json.get("remote", "")
        remote_type = remote_map.get(remote_raw, RemoteType.ON_SITE)
        if not remote_type:
            print(f"remote_type: {remote_raw}")
        return remote_type

    def get_contract_type(self, job_json: dict, title: str) -> ContractType:
        contract_map = {
            "full_time": ContractType.CDI,
            "temporary": ContractType.CDD,
            "apprenticeship": ContractType.INTERNSHIP,
            "internship": ContractType.INTERNSHIP,
            "freelance": ContractType.OTHER,
            "other": ContractType.OTHER,
        }
        contract_raw = job_json.get("contract_type", "")
        contract_type = contract_map.get(contract_raw, None)
        if contract_type is not None:
            return contract_type
        if "alternance" in title.lower() or "apprentissage" in title.lower():
            return ContractType.INTERNSHIP
        return ContractType.CDI

    def get_source_url(self, orga_raw: dict, slug: str) -> str:
        if not orga_raw or slug == "":
            return ""
        company_slug = orga_raw.get("slug", "")
        if company_slug == "":
            return ""
        url = f"{self.base_url}/fr/companies/{company_slug}/jobs/{slug}"
        return url

    def get_real_url(self) -> str:
        # TODO
        return ""

    def get_company_url(self) -> str:
        # TODO
        return ""

    def get_company_logo(self, orga_raw: dict) -> str:
        if not orga_raw:
            return ""
        logo_raw = orga_raw.get("logo", {})
        if not logo_raw:
            return ""
        logo = logo_raw.get("url", "")
        return logo
