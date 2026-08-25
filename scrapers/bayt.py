from __future__ import annotations

import random
import time
from datetime import datetime

from bs4 import BeautifulSoup

from inputs.scraper_input import ScraperInput
from models.city import City
from models.contract_type import ContractType
from models.job import Job, JobReference
from models.job_response import JobResponse
from models.salary import Salary
from scrapers.scraper import BaseScraper, SessionScraper


class BaytScraper(BaseScraper, SessionScraper):
    def __init__(self, city: City, scraper_input: ScraperInput, seen_jobs: set[str] | None = None, proxies: list[str] | str | None = None, ca_cert: str | None = None):
        BaseScraper.__init__(self, city, scraper_input, "https://www.bayt.com", seen_jobs)
        SessionScraper.__init__(self, proxies, ca_cert)
        self.delay = 2
        self.band_delay = 3

    def scrape(self) -> JobResponse:
        job_list: list[Job | JobReference] = []
        page = 1
        results_wanted = 10

        while len(job_list) < results_wanted:
            self.log.info(f"Fetching Bayt jobs page {page}")
            job_elements = self._fetch_jobs(self.scraper_input.search_term, page)
            if not job_elements:
                break

            if job_elements:
                self.log.debug(
                    "First job element snippet:\n" + job_elements[0].prettify()[:500]
                )

            initial_count = len(job_list)
            for job in job_elements:
                try:
                    job = self.process_job(job)
                    if job:
                        job_list.append(job)
                        if len(job_list) >= results_wanted:
                            break
                    else:
                        self.log.debug(
                            "Extraction returned None. Job snippet:\n"
                            + job.prettify()[:500]
                        )
                except Exception as e:
                    self.log.error(f"Bayt: Error extracting job info: {str(e)}")
                    continue

            if len(job_list) == initial_count:
                self.log.info(f"No new jobs found on page {page}. Ending pagination.")
                break

            page += 1
            time.sleep(random.uniform(self.delay, self.delay + self.band_delay))

        self.log.info("finished scraping")
        return JobResponse(job_list)

    def _fetch_jobs(self, query: str, page: int) -> list | None:
        """
        Grabs the job results for the given query and page number.
        """
        try:
            url = f"{self.base_url}/en/international/jobs/{query}-jobs/?page={page}"
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            job_listings = soup.find_all("li", attrs={"data-js-job": ""})
            self.log.debug(f"Found {len(job_listings)} job listing elements")
            return job_listings
        except Exception as e:
            self.log.error(f"Bayt: Error fetching jobs - {str(e)}")
            return None

    def process_job(self, job: BeautifulSoup) -> Job | JobReference | None:
        """
        Extracts the job information from a single job listing.
        """
        # Find the h2 element holding the title and link (no class filtering)
        job_general_information = job.find("h2")
        if not job_general_information:
            return None
        job_url = self.get_source_url(job_general_information)
        if not job_url:
            return None
        job_id = self.get_id(job_url)
        if job_id in self.seen_jobs:
            return JobReference(job_id)

        title = self.get_title(job_general_information)

        job = Job(
            id=job_id,
            source=BaytScraper.__name__,
            title=title,
            description=self.get_description(),
            company=self.get_company(job),
            city=self.city,
            address=self.get_address(job),
            posted_date=self.get_posted_date(),
            salary=self.get_salary(),
            skills=self.get_skills(),
            experience=self.get_experience(title),
            remote_type=self.get_remote_type(title),
            contract_type=self.get_contract_type(),
            source_url=job_url,
            real_url=self.get_real_url(),
            company_url=self.get_company_url(),
            company_logo=self.get_company_logo(),
        )
        self.seen_jobs.add(job_id)
        return job

    def get_company_logo(self) -> str:
        # TODO
        return ""

    def get_company_url(self) -> str:
        # TODO
        return ""

    def get_real_url(self) -> str:
        # TODO
        return ""

    def get_source_url(self, job_general_information: BeautifulSoup) -> str | None:
        a_tag = job_general_information.find("a")
        if a_tag and a_tag.has_attr("href"):
            return self.base_url + a_tag["href"].strip()
        return None

    def get_contract_type(self) -> ContractType:
        # TODO
        return ContractType.CDI

    def get_skills(self, **kwargs) -> list[str]:
        pass

    def get_salary(self) -> Salary | None:
        # TODO
        return None

    def get_posted_date(self) -> datetime | None:
        # TODO
        return None

    def get_address(self, job: BeautifulSoup) -> str:
        location_tag = job.find("div", class_=["t-mute", "t-small"])
        location = location_tag.get_text(strip=True).title() if location_tag else ""
        return location

    def get_company(self, job: BeautifulSoup) -> str:
        company_tag = job.find("div", class_=["t-nowrap", "p10l"])
        if not company_tag:
            return ""
        company_span = company_tag.find("span")
        if not company_span:
            return ""
        company_name = company_span.get_text(strip=True)
        return company_name

    def get_description(self) -> str:
        # TODO
        return ""

    def get_title(self, job_general_information: BeautifulSoup) -> str:
        job_title = job_general_information.get_text(strip=True)
        return job_title

    def get_id(self, job_url: str) -> str:
        job_id = f"bayt-{abs(hash(job_url))}"
        return job_id
