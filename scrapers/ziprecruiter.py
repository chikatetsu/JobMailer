from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from bs4 import BeautifulSoup

from inputs.scraper_input import ScraperInput
from models.city import City
from models.contract_type import ContractType
from models.job import Job, JobReference
from models.job_response import JobResponse
from models.remote_type import RemoteType
from models.salary import Salary, SalaryPeriod
from scrapers.scraper import BaseScraper, SessionScraper
from utils.util import markdown_converter, remove_attributes


class ZipRecruiter(BaseScraper, SessionScraper):
    def __init__(self, city: City, scraper_input: ScraperInput, seen_jobs: set[str] | None = None, proxies: list[str] | str | None = None, ca_cert: str | None = None):
        """
        Initializes ZipRecruiterScraper with the ZipRecruiter job search url
        """
        BaseScraper.__init__(self, city, scraper_input, "https://www.ziprecruiter.com", seen_jobs=seen_jobs)
        SessionScraper.__init__(self, proxies, ca_cert)
        self.session.headers.update({
            "Host": "api.ziprecruiter.com",
            "accept": "*/*",
            "x-zr-zva-override": "100000000;vid:ZT1huzm_EQlDTVEc",
            "x-pushnotificationid": "0ff4983d38d7fc5b3370297f2bcffcf4b3321c418f5c22dd152a0264707602a0",
            "x-deviceid": "D77B3A92-E589-46A4-8A39-6EF6F1D86006",
            "user-agent": "Job Search/87.0 (iPhone; CPU iOS 16_6_1 like Mac OS X)",
            "authorization": "Basic YTBlZjMyZDYtN2I0Yy00MWVkLWEyODMtYTI1NDAzMzI0YTcyOg==",
            "accept-language": "en-US,en;q=0.9",
        })
        self.api_url = "https://api.ziprecruiter.com"
        self._get_cookies()
        self.delay = 5
        self.jobs_per_page = 20

    def scrape(self) -> JobResponse:
        """
        Scrapes ZipRecruiter for jobs with scraper_input criteria.
        :return: JobResponse containing a list of jobs.
        """
        job_list: list[Job | JobReference] = []
        continue_token = None

        for page in range(1, sys.maxsize):
            if page > 1:
                time.sleep(self.delay)
            self.log.info(f"search page: {page}")
            jobs_on_page, continue_token = self._find_jobs_in_page(continue_token)
            if jobs_on_page:
                job_list.extend(jobs_on_page)
            else:
                break
            if not continue_token:
                break
        self.log.info("finished scraping")
        return JobResponse(job_list)

    def process_job(self, job: dict) -> Job | JobReference | None:
        """
        Processes an individual job dict from the response
        """
        job_id = self.get_id(job)
        if job_id in self.seen_jobs:
            return JobReference(job_id)

        job_url = self.get_source_url(job)
        description = self.get_description(job)
        description_full, job_url_direct = self._get_descr(job_url)
        title = self.get_title(job)

        job = Job(
            id=job_id,
            source=ZipRecruiter.__name__,
            title=title,
            description=description,
            company=self.get_company(job),
            city=self.city,
            address=self.get_address(job),
            posted_date=self.get_posted_date(job),
            salary=self.get_salary(job),
            skills=self.get_skills(),
            experience=self.get_experience(title),
            remote_type=self.get_remote_type(),
            contract_type=self.get_contract_type(),
            source_url=job_url,
            real_url=job_url_direct,
            company_url=self.get_company_url(),
            company_logo=self.get_company_logo(),
        )
        self.seen_jobs.add(job_id)
        return job

    def get_id(self, job: dict) -> str:
        job_id = f'zr-{job["listing_key"]}'
        return job_id

    def get_title(self, job: dict) -> str:
        title = job.get("name", "")
        return title

    def get_description(self, job: dict) -> str:
        description = job.get("job_description", "").strip()
        # if self.scraper_input.description_format == FormatType.MARKDOWN:
        description = markdown_converter(description)
        return description

    def get_company(self, job: dict) -> str:
        company = job.get("hiring_company", {}).get("name", "")
        return company

    def get_address(self, job: dict) -> str:
        city = job.get("job_city")
        if city is None:
            return ""
        return city.title()

    def get_posted_date(self, job: dict) -> datetime | None:
        date_posted = datetime.fromisoformat(job["posted_time"].rstrip("Z"))
        return date_posted

    def get_salary(self, job: dict) -> Salary:
        period = job.get("compensation_interval")
        period = SalaryPeriod.YEARLY if period == "annual" else SalaryPeriod.MONTHLY
        if not "compensation_min" in job or "compensation_max" in job:
            return None
        else:
            min_amount = int(job["compensation_min"])
            max_amount = int(job["compensation_max"])
            currency = job.get("compensation_currency", "€")
            return Salary.from_raw(min_amount, max_amount, period, currency)

    def get_skills(self) -> list[str]:
        # TODO
        return []

    def get_remote_type(self) -> RemoteType:
        # TODO
        return RemoteType.ON_SITE

    def get_contract_type(self) -> ContractType:
        # TODO
        return ContractType.CDI

    def get_source_url(self, job: dict) -> str:
        url = f"{self.base_url}/jobs//j?lvk={job['listing_key']}"
        return url

    def get_real_url(self) -> str:
        pass

    def get_company_url(self) -> str:
        pass

    def get_company_logo(self) -> str:
        pass

    def _find_jobs_in_page(self, continue_token: str | None = None) -> tuple[list[Job], str | None]:
        """
        Scrapes a page of ZipRecruiter for jobs with scraper_input criteria
        :param continue_token:
        :return: jobs found on page
        """
        jobs_list = []
        params = self.add_params()
        if continue_token:
            params["continue_from"] = continue_token
        try:
            res = self.session.get(f"{self.api_url}/jobs-app/jobs", params=params)
            if res.status_code not in range(200, 400):
                if res.status_code == 429:
                    err = "429 Response - Blocked by ZipRecruiter for too many requests"
                else:
                    err = f"ZipRecruiter response status code {res.status_code}"
                    err += f" with response: {res.text}"  # ZipRecruiter likely not available in EU
                self.log.error(err)
                return jobs_list, ""
        except Exception as e:
            if "Proxy responded with" in str(e):
                self.log.error(f"Bad proxy")
            else:
                self.log.error(e)
            return jobs_list, ""

        res_data = res.json()
        jobs_list = res_data.get("jobs", [])
        next_continue_token = res_data.get("continue", None)
        with ThreadPoolExecutor(max_workers=self.jobs_per_page) as executor:
            job_results = [executor.submit(self.process_job, job) for job in jobs_list]

        job_list = list(filter(None, (result.result() for result in job_results)))
        return job_list, next_continue_token

    def add_params(self) -> dict[str, str | int]:
        params: dict[str, str | int | None] = {
            "search": self.scraper_input.search_term,
            "location": str(self.city),
            "radius": self.scraper_input.distance(),
        }
        return {k: v for k, v in params.items() if v is not None}

    def _get_descr(self, job_url):
        res = self.session.get(job_url, allow_redirects=True)
        description_full = job_url_direct = None
        if res.ok:
            soup = BeautifulSoup(res.text, "html.parser")
            job_descr_div = soup.find("div", class_="job_description")
            company_descr_section = soup.find("section", class_="company_description")
            job_description_clean = (
                remove_attributes(job_descr_div).prettify(formatter="html")
                if job_descr_div
                else ""
            )
            company_description_clean = (
                remove_attributes(company_descr_section).prettify(formatter="html")
                if company_descr_section
                else ""
            )
            description_full = job_description_clean + company_description_clean

            try:
                script_tag = soup.find("script", type="application/json")
                if script_tag:
                    job_json = json.loads(script_tag.string)
                    job_url_val = job_json["model"].get("saveJobURL", "")
                    m = re.search(r"job_url=(.+)", job_url_val)
                    if m:
                        job_url_direct = m.group(1)
            except Exception as e:
                self.log.warning(f"Exception while parsing job description: {e}")
                job_url_direct = None

            # if self.scraper_input.description_format == FormatType.MARKDOWN:
            description_full = markdown_converter(description_full)

        return description_full, job_url_direct

    def _get_cookies(self):
        """
        Sends a session event to the API with device properties.
        """
        url = f"{self.api_url}/jobs-app/event"
        self.session.post(
            url,
            data=[
            ("event_type", "session"),
            ("logged_in", "false"),
            ("number_of_retry", "1"),
            ("property", "model:iPhone"),
            ("property", "os:iOS"),
            ("property", "locale:en_us"),
            ("property", "app_build_number:4734"),
            ("property", "app_version:91.0"),
            ("property", "manufacturer:Apple"),
            ("property", "timestamp:2025-01-12T12:04:42-06:00"),
            ("property", "screen_height:852"),
            ("property", "os_version:16.6.1"),
            ("property", "source:install"),
            ("property", "screen_width:393"),
            ("property", "device_model:iPhone 14 Pro"),
            ("property", "brand:Apple"),
        ])
