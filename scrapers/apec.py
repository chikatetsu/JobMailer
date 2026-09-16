import sys
from datetime import datetime
from urllib.parse import urlencode, quote, urlparse

from bs4 import BeautifulSoup, Tag
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from inputs.scraper_input import ScraperInput
from models.city import City
from models.contract_type import ContractType
from models.job import Job, JobReference
from models.job_response import JobResponse
from models.salary import Salary
from scrapers.scraper import BaseScraper, SeleniumScraper


class Apec(BaseScraper, SeleniumScraper):
    def __init__(self, city: City, scraper_input: ScraperInput, seen_jobs: set[str] | None = None):
        BaseScraper.__init__(self, city, scraper_input, "https://www.apec.fr", seen_jobs=seen_jobs)
        SeleniumScraper.__init__(self)

    def _build_url(self, page: int) -> str:
        """Construit l'URL Apec à partir d'un mot-clé et d'une ville"""
        params = {
            "motsCles": self.scraper_input.search_term,
            "lieux": self._city_to_apec_code(self.scraper_input.cities[0]),
            "page": page,
            "distance": self.scraper_input.distance([0, 5, 10, 15, 25, 50, 100])
        }
        url = f"{self.base_url}/candidat/recherche-emploi.html/emploi?{urlencode(params, quote_via=quote)}"
        return url

    def _city_to_apec_code(self, city: City) -> str:
        city_apec_code_map = {
            City.AIX_EN_PROVENCE: "564326",
            City.BORDEAUX: "572920",
            City.BOULOGNE_BILLANCOURT: "596193",
            City.BREST: "571188",
            City.PARIS: "75",
            City.LYON: "596717",
            City.TOULOUSE: "572357",
            City.NANTES: "577013",
            City.MONTPELLIER: "573572",
            City.STRASBOURG: "587878",
            City.LILLE: "583319",
            City.RENNES: "573974",
            City.NANTERRE: "596212"
        }
        apec_code = city_apec_code_map.get(city, "")
        if apec_code == "":
            self.log.error(f"No apec code for city \"{city}\"")
        return apec_code

    def scrape(self) -> JobResponse:
        job_response = []
        try:
            for page in range(0, sys.maxsize):
                url = self._build_url(page)
                self.log.info(f"scraping page {page + 1}...")
                self.driver.get(url)

                wait = WebDriverWait(self.driver, 15)
                wait.until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, 'a[queryparamshandling="merge"]')
                    )
                )

                soup = BeautifulSoup(self.driver.page_source, "html.parser")

                job_cards = soup.find_all("a", attrs={"queryparamshandling": "merge"})
                if not job_cards:
                    self.log.warning("no job cards found")
                    break

                jobs = []
                for card in job_cards:
                    job = self.process_job(card)
                    jobs.append(job)
                if not jobs or len(jobs) == 0:
                    self.log.warning("no jobs found")
                    break
                job_response.extend(jobs)
        except Exception as e:
            self.log.error(e)
        finally:
            self.driver.close()

        self.log.info("finished scraping")
        return JobResponse(job_response)

    def process_job(self, job_card: Tag) -> Job | JobReference:
        source_url = self.get_source_url(job_card)
        job_id = self.get_id(source_url)
        if job_id in self.seen_jobs:
            return JobReference(job_id)

        title = self.get_title(job_card)
        description = self.get_description(job_card)
        details = job_card.find_all("li")
        job = Job(
            id=job_id,
            source=Apec.__name__,
            title=title,
            description=description,
            company=self.get_company(job_card),
            city=self.city,
            address=self.get_address(details),
            posted_date=self.get_posted_date(details),
            salary=self.get_salary(details),
            skills=self.get_skills(job_card),
            experience=self.get_experience(title),
            remote_type=self.get_remote_type(description),
            contract_type=self.get_contract_type(details),
            source_url=source_url,
            real_url=self.get_real_url(job_card),
            company_url=self.get_company_url(job_card),
            company_logo=self.get_company_logo(job_card),
        )
        self.seen_jobs.add(job_id)
        return job

    def get_id(self, link: str) -> str:
        id_raw = urlparse(link).path.split("/")[-1]
        return f"apec_{id_raw}"

    def get_title(self, job_card: Tag) -> str:
        title_raw = job_card.find("h2")
        if not title_raw:
            return ""
        return title_raw.text.strip()

    def get_description(self, job_card: Tag) -> str:
        description_raw = job_card.find("p", class_="card-offer__description")
        if not description_raw:
            return ""
        return description_raw.text.strip()

    def get_company(self, job_card: Tag) -> str:
        company_raw = job_card.find("p", class_="card-offer__company")
        if not company_raw:
            return ""
        return company_raw.text.strip()

    def get_address(self, details: list[Tag]) -> str:
        if len(details) < 3:
            return ""
        address = details[2].text.strip()
        return address

    def get_posted_date(self, details: list[Tag]) -> datetime:
        if len(details) < 4:
            return datetime.now()
        posted_date_raw = details[3].text.strip()
        splitted_posted_date = posted_date_raw.split("/")
        posted_date = datetime(day=int(splitted_posted_date[0]), month=int(splitted_posted_date[1]), year=int(splitted_posted_date[2]))
        return posted_date

    def get_salary(self, details: list[Tag]) -> Salary | None:
        if len(details) < 1:
            return None
        salary_raw = details[0].text.strip()
        if salary_raw == "A négocier":
            return None
        if salary_raw.startswith("A partir de "):
            min_amount = int(salary_raw.replace("A partir de", "").replace(" k€ brut annuel", "").strip())
            salary = Salary(min_amount=min_amount, max_amount=min_amount)
            return salary
        splitted_salary = salary_raw.split(" ")
        salary = Salary(min_amount=int(splitted_salary[0]), max_amount=int(splitted_salary[2]))
        return salary

    def get_skills(self, job_card: Tag) -> list[str]:
        # TODO
        return []

    def get_contract_type(self, details: list[Tag]) -> ContractType:
        if len(details) < 2:
            return ContractType.OTHER
        contract_type_raw = details[1].text.strip()
        contract_map = {
            "CDI": ContractType.CDI,
            "CDD": ContractType.CDD,
            "Alternance": ContractType.INTERNSHIP,
            "Intérim": ContractType.INTERIM
        }
        contract = contract_map.get(contract_type_raw, ContractType.CDI)
        return contract

    def get_source_url(self, job_card: Tag) -> str:
        url = job_card.get("href", "")
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
        default = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTcpPW7qTRZ9mpemQA7MmxE7Mn6BtN3_A7j0k5P0QBEnTIO0wCNpmCLGGM&s=10"
        logo_raw = job_card.find("img", attrs={"alt": "Logo société"})
        if not logo_raw or len(logo_raw) == 0:
            return default
        logo = str(logo_raw.get("src", default))
        return logo
