import re
import time
from datetime import datetime
from urllib import parse

from bs4 import BeautifulSoup, Tag
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from inputs.scraper_input import ScraperInput
from models.city import City
from models.contract_type import ContractType
from models.job import Job, JobReference
from models.job_response import JobResponse
from models.salary import Salary, SalaryPeriod
from .scraper import BaseScraper, SeleniumScraper


class Indeed(BaseScraper, SeleniumScraper):
    def __init__(self, city: City, scraper_input: ScraperInput, seen_jobs: set[str] | None = None):
        BaseScraper.__init__(self, city, scraper_input, f"https://fr.indeed.com", seen_jobs=seen_jobs)
        SeleniumScraper.__init__(self)

    def _build_url(self) -> str:
        return (
            f"{self.base_url}/jobs"
            f"?q={parse.quote(self.scraper_input.search_term)}"
            f"&l={parse.quote(str(self.city))}"
            f"&radius={self.scraper_input.distance([0, 5, 10, 15, 25, 35, 50, 100])}"
        )

    def _handle_captcha(self) -> bool:
        if "captcha" in self.driver.current_url.lower() or "robot" in self.driver.page_source.lower():
            print("Captcha détecté — résous-le manuellement.")
            input("Appuie sur Entrée une fois passé...")
            return True
        return False

    def scrape(self) -> JobResponse:
        jobs = []

        try:
            for page in range(1, 50):
                url = self._build_url()
                print(f"Page {page} : {url}")
                self.driver.get(url)
                time.sleep(self._random_delay())
                # self._handle_captcha()

                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#mosaic-provider-jobcards"))
                    )
                except Exception as e:
                    print(f"Aucune offre trouvée page {page}, arrêt : {e}")
                    break

                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

                soup = BeautifulSoup(self.driver.page_source, "html.parser")

                jobs = []
                job_cards = soup.find_all("td", class_="resultContent")
                print(job_cards)

                for card in job_cards:
                    job = self.process_job(card)
                    jobs.append(job)
                print(jobs)
                if not jobs:
                    break

                jobs.extend(jobs)
                print(f"{len(jobs)} offres récupérées")
                self.next_page()
        finally:
            self.driver.quit()

        return JobResponse(jobs)

    def process_job(self, job_card: Tag) -> Job | JobReference:
        job_link = job_card.find("a", class_="jcs-JobTitle")
        job_id = self.get_id(job_link)
        if job_id in self.seen_jobs:
            return JobReference(job_id)

        title = self.get_title(job_link)
        description = self.get_description(job_card)
        text = title + description
        job = Job(
            id=job_id,
            source=Indeed.__name__,
            title=title,
            description=description,
            company=self.get_company(job_card),
            city=self.city,
            address=self.get_address(job_card),
            posted_date=self.get_posted_date(),
            salary=self.get_salary(job_card),
            skills=self.get_skills(),
            experience=self.get_experience(text),
            remote_type=self.get_remote_type(text),
            contract_type=self.get_contract_type(job_card),
            source_url=self.get_source_url(job_link),
            real_url=self.get_real_url(),
            company_url=self.get_company_url(),
            company_logo=self.get_company_logo(job_card)
        )
        self.seen_jobs.add(job_id)
        return job

    def next_page(self):
        self.driver.find_element(By.CSS_SELECTOR, '[aria-label="Page suivante"]').click()

    def get_id(self, job_title: Tag | None) -> str:
        if not job_title:
            return ""
        return f"in_{job_title.get('data-jk')}"

    def get_title(self, job_title: Tag | None) -> str:
        if not job_title:
            return ""
        return job_title.get_text(strip=True)

    def get_description(self, job_card: Tag) -> str:
        description = job_card.find("div", attrs={"data-testid": "belowJobSnippet"})
        if not description:
            return ""
        return description.get_text(strip=True)

    def get_company(self, job_card: Tag) -> str:
        company = job_card.find("span", attrs={"data-testid": "company-name"})
        if not company:
            return ""
        return company.get_text(strip=True)

    def get_address(self, job_card: Tag) -> str:
        location_raw = job_card.find("div", attrs={"data-testid": "text-location"})
        if not location_raw:
            return ""
        city = location_raw.get_text(strip=True).title()
        return city

    def get_posted_date(self) -> datetime | None:
        # TODO
        return None

    def get_salary(self, job_card: Tag) -> Salary | None:
        salary_raw = job_card.find("li", attrs={"data-testid": "salary-snippet-container"})
        if not salary_raw:
            return None
        salary = salary_raw.get_text(strip=True)

        pattern = r"De\s+(?P<min>\d+(?:\s\d+)?)\s+€\s+à\s+(?P<max>\d+(?:\s\d+)?)\s+€\s+par\s+(?P<period>ans|mois)"
        match = re.search(pattern, salary)
        if not match:
            return None
        period = match.group("period")
        min_amount = int(match.group("min").replace(" ", ""))
        max_amount = int(match.group("max").replace(" ", ""))
        if period == "ans":
            return Salary.from_raw(min_amount, max_amount, SalaryPeriod.YEARLY)
        elif period == "mois":
            return Salary.from_raw(min_amount, max_amount, SalaryPeriod.MONTHLY)
        return None

    def get_skills(self) -> list[str]:
        # TODO
        return []

    def get_contract_type(self, job_card: Tag) -> ContractType:
        elements = job_card.find_all("li", attrs={"data-testid": "attribute_snippet_testid"})
        if not elements:
            return ContractType.OTHER
        contract_map = {
            "CDI": ContractType.CDI,
            "Alternance": ContractType.INTERNSHIP,
            "Contrat d'apprentissage": ContractType.INTERNSHIP,
            "Temps plein": ContractType.CDI,
            "CDD": ContractType.CDD,
        }
        for element in elements:
            text = element.get_text(strip=True)
            if not text.startswith("De "):
                text = text.replace(" + 1", "")
                contract_type = contract_map.get(text, ContractType.OTHER)
                return contract_type
        return ContractType.OTHER

    def get_source_url(self, job_title: Tag | None) -> str:
        if not job_title:
            return ""
        return f"{self.base_url}/viewjob?jk={job_title.get('data-jk')}"

    def get_real_url(self) -> str:
        # TODO
        return ""

    def get_company_url(self) -> str:
        # TODO
        return ""

    def get_company_logo(self, job_card: Tag) -> str:
        default = "https://media.licdn.com/dms/image/v2/C4E0BAQGRyD6gjS54VA/company-logo_100_100/company-logo_100_100/0/1658856556669/indeed_com_logo?e=1781740800&v=beta&t=ravMfYxuJkEA6mIkq2MyKOOI-Cg6AZBFOWr3v9WMiV8"
        img = job_card.find("img")
        if not img:
            return default
        company_logo = str(img.get("src", default))
        return company_logo
