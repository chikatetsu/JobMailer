import re
import sys
import time
from datetime import datetime, timedelta
from urllib import parse

from bs4 import BeautifulSoup, Tag

from inputs.scraper_input import ScraperInput
from models.city import City
from models.contract_type import ContractType
from models.experience import Experience
from models.job import Job, JobReference
from models.job_response import JobResponse
from models.remote_type import RemoteType
from models.salary import Salary, SalaryPeriod
from .scraper import BaseScraper, SeleniumScraper


class HelloWork(BaseScraper, SeleniumScraper):
    def __init__(self, city: City, scraper_input: ScraperInput, seen_jobs: set[str] | None = None):
        BaseScraper.__init__(self, city, scraper_input, "https://www.hellowork.com", seen_jobs=seen_jobs)
        SeleniumScraper.__init__(self)
        self.time_limit = datetime.now() + timedelta(minutes=30)

    def _build_url(self, page: int) -> str:
        return (
            f"{self.base_url}/fr-fr/emploi/recherche.html"
            f"?k={parse.quote(self.scraper_input.search_term)}"
            f"&l={parse.quote(str(self.city))}"
            f"&ray={self.scraper_input.distance([0, 5, 10, 20, 50])}"
            f"&p={page}"
        )

    def scrape(self) -> JobResponse:
        job_response = []
        try:
            for page in range(1, sys.maxsize):
                if datetime.now() >= self.time_limit:
                    self.log.warning("Timed out")
                    break

                url = self._build_url(page)
                self.log.info(f"scraping page {page}...")

                self.driver.get(url)
                soup = BeautifulSoup(self.driver.page_source, "html.parser")

                list_container = soup.find("ul", attrs={"data-id-storage-local-storage-key-param": "visited_offers"})
                if not list_container:
                    self.log.warning("ul not found")
                    break
                job_cards = list_container.find_all("li", attrs={"data-id-storage-target": "item"})

                jobs = []
                for card in job_cards:
                    job = self.process_job(card)
                    if job is not None:
                        jobs.append(job)
                if not jobs or len(jobs) == 0:
                    break
                job_response.extend(jobs)
        except Exception as e:
            self.log.error(e)
        finally:
            self.driver.close()

        self.log.info("finished scraping")
        return JobResponse(job_response)

    def process_job(self, job_card: Tag) -> Job | JobReference | None:
        job_id = self.get_id(job_card)
        if job_id in self.seen_jobs:
            return JobReference(job_id)

        link = job_card.find("a")
        title = self.get_title(link)
        source_url = self.get_source_url(link)
        time.sleep(self._random_delay(0.0, 1.5))
        self.driver.get(source_url)
        more_soup = BeautifulSoup(self.driver.page_source, "html.parser")

        job = Job(
            id=job_id,
            source=HelloWork.__name__,
            title=title,
            description=self.get_description(more_soup),
            company=self.get_company(link),
            city=self.city,
            address=self.get_address(job_card),
            posted_date=self.get_posted_date(job_card),
            salary=self.get_salary(job_card),
            skills=self.get_skills(job_card),
            experience=self.get_experience(more_soup, title),
            remote_type=self.get_remote_type(job_card),
            contract_type=self.get_contract_type(job_card, title),
            source_url=source_url,
            real_url=self.get_real_url(job_card),
            company_url=self.get_company_url(job_card),
            company_logo=self.get_company_logo(job_card)
        )
        self.seen_jobs.add(job_id)
        return job

    def get_id(self, job_card: Tag) -> str:
        id_raw = job_card.get("data-id-storage-item-id")
        return f"hw_{id_raw}"

    def get_title(self, link: Tag | None) -> str:
        if not link:
            return ""
        paras = link.find_all("p")
        if not paras:
            return ""
        title = paras[0].get_text(strip=True)
        return title

    def get_description(self, soup: BeautifulSoup) -> str:
        desc_raw = soup.find("div", id="offer-panel")
        if not desc_raw:
            return ""
        paras = desc_raw.find_all("p")
        description = ""
        for para in paras[:-1]:
            description += para.get_text(strip=True)
        return description

    def get_company(self, link: Tag | None) -> str:
        if not link:
            return ""
        paras = link.find_all("p")
        if not paras or len(paras) < 2:
            return ""
        company = paras[1].get_text(strip=True)
        return company

    def get_address(self, job_card: Tag) -> str:
        location_raw = job_card.find("div", attrs={"data-cy": "localisationCard"})
        if not location_raw:
            return ""
        city = location_raw.get_text(strip=True).title()
        return city

    def get_posted_date(self, job_card: Tag) -> datetime | None:
        date_raw = job_card.find("div", class_=["typo-s", "text-grey-500", "pl-1", "pt-1"])
        if not date_raw:
            return None
        pattern = r"il\s+y\s+a\s+(?P<value>\d+(?:\d+)?)\s+(?P<unit>heure|jour|mois|an)"
        match = re.search(pattern, date_raw.get_text(strip=True))
        if not match:
            return None
        value = float(match.group("value"))
        unit = match.group("unit")
        now = datetime.now()
        if unit == "heure":
            return now - timedelta(hours=value)
        elif unit == "jour":
            return now - timedelta(days=value)
        elif unit == "mois":
            return now - timedelta(days=value * 30)
        elif unit == "an":
            return now - timedelta(days=value * 365)
        return None

    def get_salary(self, job_card: Tag) -> Salary | None:
        salary_raw = job_card.find("div", class_="readonly tag-secondary-s typo-s-bold w-fit border-0")
        if not salary_raw:
            return None
        amount_pattern = r"\d[\d\s]*(?:,\d+)?"
        pattern = (
            rf"(?P<min1>{amount_pattern})\s+-\s+(?P<max1>{amount_pattern})\s+€\s*/\s*(?P<period1>an|mois|jour)"
            rf"|(?P<single2>{amount_pattern})\s+€\s*/\s*(?P<period2>an|mois|jour)"
            rf"|(?P<min3>{amount_pattern})\s+-\s+(?P<max3>{amount_pattern})\s+€\s*/\s*(?P<period3>heure)"
            rf"|(?P<single4>{amount_pattern})\s+€\s*/\s*(?P<period4>heure)"
        )
        match = re.search(pattern, salary_raw.get_text(strip=True))
        if not match:
            self.log.warning(f"Pattern matching not working for salary : {salary_raw.get_text(strip=True)}")
            return None

        def parse_amount(raw: str) -> float:
            # Remove thousands spaces, replace decimal comma with dot
            return float(raw.replace(" ", "").replace(" ", "").replace(",", "."))

        if match.group("single4"):
            amount = parse_amount(match.group("single4"))
            min_amount = max_amount = amount
            period = match.group("period4")
        elif match.group("min3"):
            min_amount = parse_amount(match.group("min3"))
            max_amount = parse_amount(match.group("max3"))
            period = match.group("period3")
        elif match.group("single2"):
            amount = parse_amount(match.group("single2"))
            min_amount = max_amount = amount
            period = match.group("period2")
        else:
            min_amount = parse_amount(match.group("min1"))
            max_amount = parse_amount(match.group("max1"))
            period = match.group("period1")

        period_map = {
            "an": SalaryPeriod.YEARLY,
            "mois": SalaryPeriod.MONTHLY,
            "jour": SalaryPeriod.DAILY,
            "heure": SalaryPeriod.HOURLY
        }

        if period not in period_map:
            self.log.warning(f"Wrong salary period '{period}' for salary: {salary_raw.get_text(strip=True)}")
            return None

        return Salary.from_raw(min_amount, max_amount, period_map[period])

    def get_skills(self, job_card: Tag) -> list[str]:
        # TODO
        return []

    def get_experience(self, soup: BeautifulSoup, title: str) -> Experience:
        list_info = soup.find_all("li", class_="block tag-secondary-s border-0 readonly")
        if not list_info:
            return BaseScraper.get_experience(self, title)
        for info_raw in list_info:
            info = info_raw.get_text(strip=True)
            if info.startswith("Exp. "):
                splitted = info.split(" ")
                if splitted[1].isdigit():
                    years_required = int(info.split(" ")[1])
                elif splitted[2].isdigit():
                    years_required = int(info.split(" ")[2])
                else:
                    return BaseScraper.get_experience(self, title)
                return Experience.from_years_required(years_required)
        return BaseScraper.get_experience(self, title)

    def get_contract_type(self, job_card: Tag, title: str) -> ContractType:
        contract_raw = job_card.find("div", attrs={"data-cy": "contractCard"})
        if not contract_raw:
            if "alternance" in title.lower() or "apprentissage" in title.lower():
                return ContractType.INTERNSHIP
            return ContractType.CDI
        contract_map = {
            "CDI": ContractType.CDI,
            "Alternance": ContractType.INTERNSHIP,
            "CDD": ContractType.CDD,
            "Intérim": ContractType.INTERIM,
            "Stage": ContractType.INTERNSHIP,
            "Indépendant": ContractType.OTHER,
            "Franchise": ContractType.OTHER,
            "Associé": ContractType.OTHER,
            "Fonctionnaire": ContractType.CDI,
            "Freelance": ContractType.OTHER,
            "Stage de lycée": ContractType.INTERNSHIP,
        }
        contract = contract_map.get(contract_raw.get_text(strip=True), ContractType.CDI)
        return contract

    def get_remote_type(self, job_card: Tag) -> RemoteType:
        remote_type_raw = job_card.find("div", attrs={"data-cy": "contractTag"})
        if not remote_type_raw:
            return RemoteType.ON_SITE
        remote_map = {
            "Complet": RemoteType.REMOTE,
            "Partiel": RemoteType.HYBRID,
            "Occasionnel": RemoteType.HYBRID,
            "Pas de télétravail": RemoteType.ON_SITE
        }
        remote_type = remote_map.get(remote_type_raw.get_text(strip=True), RemoteType.ON_SITE)
        return remote_type

    def get_source_url(self, link: Tag | None) -> str:
        if not link:
            return ""
        url = link.get("href", "")
        if url == "":
            return ""
        return f"{self.base_url}{url}"

    def get_real_url(self, job_card: Tag) -> str:
        # TODO
        return ""

    def get_company_url(self, job_card: Tag) -> str:
        # TODO
        return ""

    def get_company_logo(self, job_card: Tag) -> str:
        default = "https://upload.wikimedia.org/wikipedia/commons/e/e1/LOGO_HelloWork_Activit%C3%A9s.png"
        logo_raw = job_card.find_all("img")
        if not logo_raw or len(logo_raw) < 2:
            return default
        logo = str(logo_raw[1].get("src", default))
        return logo
