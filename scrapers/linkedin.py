from __future__ import annotations

import time
from datetime import datetime
from urllib.parse import urlparse, urlunparse, unquote

import regex as re
from bs4 import BeautifulSoup
from bs4.element import Tag

from inputs.scraper_input import ScraperInput
from models.city import City
from models.contract_type import ContractType
from models.experience import Experience
from models.job import Job, JobReference
from models.job_response import JobResponse
from models.salary import Salary
from utils.util import markdown_converter, remove_attributes
from .scraper import BaseScraper, SessionScraper

HEADERS = {
    "authority": "www.linkedin.com",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

class LinkedIn(BaseScraper, SessionScraper):
    def __init__(self, city: City, scraper_input: ScraperInput, seen_jobs: set[str] | None = None, proxies: list[str] | str | None = None, ca_cert: str | None = None):
        BaseScraper.__init__(self, city, scraper_input, "https://www.linkedin.com", seen_jobs=seen_jobs)
        SessionScraper.__init__(self, proxies, ca_cert)
        self.session.headers.update(HEADERS)
        self.delay = 3
        self.band_delay = 4
        self.jobs_per_page = 25
        self.job_url_direct_regex = re.compile(r'(?<=\?url=)[^"]+')

    def scrape(self) -> JobResponse:
        """
        Scrapes LinkedIn for jobs with scraper_input criteria
        :return: JobResponse
        """
        job_list: list[Job | JobReference] = []
        start = 0
        request_count = 0
        while start < 1000:
            request_count += 1
            self.log.info(f"search page: {request_count}")
            params = {
                "keywords": self.scraper_input.search_term,
                "location": str(self.city),
                "distance": self.scraper_input.distance(),
                "pageNum": 0,
                "start": start,
            }

            params = {k: v for k, v in params.items() if v is not None}
            try:
                response = self.session.get(
                    f"{self.base_url}/jobs-guest/jobs/api/seeMoreJobPostings/search?",
                    params=params,
                    timeout=10,
                )
                if response.status_code not in range(200, 400):
                    if response.status_code == 429:
                        err = (
                            f"429 Response - Blocked by LinkedIn for too many requests"
                        )
                    else:
                        err = f"LinkedIn response status code {response.status_code}"
                        err += f" - {response.text}"
                    self.log.error(err)
                    return JobResponse(job_list)
            except Exception as e:
                if "Proxy responded with" in str(e):
                    self.log.error("Bad proxy")
                else:
                    self.log.error(e)
                return JobResponse(job_list)

            soup = BeautifulSoup(response.text, "html.parser")
            job_cards = soup.find_all("div", class_="base-search-card")
            if len(job_cards) == 0:
                return JobResponse(job_list)

            jobs = []
            for job_card in job_cards:
                job = self.process_job(job_card)
                if job:
                    jobs.append(job)
                if start >= 1000:
                    break
            job_list.extend(jobs)

            if start < 1000:
                time.sleep(self._random_delay(self.delay, self.delay + self.band_delay))
                start += len(job_cards)

        self.log.info("finished scraping")
        return JobResponse(job_list)

    def process_job(self, job_card: Tag) -> Job | JobReference | None:
        job_id = self.get_id(job_card)
        if job_id == "":
            return None
        if job_id in self.seen_jobs:
            return JobReference(job_id)

        title = self.get_title(job_card)
        job_url = self.get_source_url(job_id)

        company_tag = job_card.find("h4", class_="base-search-card__subtitle")
        company_a_tag = company_tag.find("a") if company_tag else None

        metadata_card = job_card.find("div", class_="base-search-card__metadata")
        address = self.get_address(metadata_card)

        try:
            response = self.session.get(job_url, timeout=5)
            response.raise_for_status()
            if "linkedin.com/signup" in response.url:
                raise Exception("Cannot get more info on the job : signup page")
            more_soup = BeautifulSoup(response.text, "html.parser")
            description = self.get_description(more_soup)
            experience = self.get_experience(more_soup, title)
            contract_type = self.get_contract_type(more_soup, title)
            real_url = self.get_real_url(more_soup)
            company_logo = self.get_company_logo(more_soup)
        except Exception as e:
            self.log.error(e)
            description = ""
            experience = BaseScraper.get_experience(self, title)
            contract_type = ContractType.CDI
            real_url = ""
            company_logo = ""

        job = Job(
            id=job_id,
            source=LinkedIn.__name__,
            title=title,
            description=description,
            company=self.get_company(company_a_tag),
            city=self.city,
            address=address,
            posted_date=self.get_posted_date(metadata_card),
            salary=self.get_salary(job_card),
            skills=self.get_skills(),
            experience=experience,
            remote_type=self.get_remote_type(description),
            contract_type=contract_type,
            source_url=job_url,
            real_url=real_url,
            company_url=self.get_company_url(company_a_tag),
            company_logo=company_logo,
        )
        self.seen_jobs.add(job_id)
        return job


    def get_company_logo(self, soup: BeautifulSoup) -> str:
        default = "https://media.licdn.com/dms/image/v2/C560BAQHaVYd13rRz3A/company-logo_100_100/company-logo_100_100/0/1638831590218/linkedin_logo?e=1781740800&v=beta&t=MkuyjG2GIZxMOHDt-UlAX3HKOlVDsj5HDkz3WX1YMcw"
        logo_image = soup.find("img", {"class": "artdeco-entity-image"})
        if logo_image:
            return str(logo_image.get("data-delayed-url", default))
        return default

    def get_company_url(self, company_a_tag: Tag | None) -> str:
        if company_a_tag and company_a_tag.has_attr("href"):
            return str(urlunparse(urlparse(company_a_tag.get("href"))._replace(query="")))
        return ""

    def get_real_url(self, soup: BeautifulSoup) -> str:
        job_url_direct = ""
        job_url_direct_content = soup.find("code", id="applyUrl")
        if job_url_direct_content:
            job_url_direct_match = self.job_url_direct_regex.search(
                job_url_direct_content.decode_contents().strip()
            )
            if job_url_direct_match:
                job_url_direct = unquote(job_url_direct_match.group())
        return job_url_direct

    def get_source_url(self, job_id) -> str:
        return f"{self.base_url}/jobs/view/{job_id}"

    def get_contract_type(self, soup_job_type: BeautifulSoup, title: str) -> ContractType:
        """
        Gets the job type from job page
        :param soup_job_type:
        :param title:
        :return: ContractType
        """
        h3_tag = soup_job_type.find("h3", class_="description__job-criteria-subheader", string=lambda text: "Employment type" in text)
        if not h3_tag:
            return ContractType.CDI
        employment_type_span = h3_tag.find_next_sibling("span", class_=["description__job-criteria-text", "description__job-criteria-text--criteria"])
        if not employment_type_span:
            return ContractType.CDI
        employment_type = employment_type_span.get_text(strip=True).lower().replace("-", "")
        contract_map = {
            "fulltime": ContractType.CDI,
            "internship": ContractType.INTERNSHIP,
            "other": ContractType.OTHER,
            "volunteer": ContractType.OTHER,
        }
        contract = contract_map.get(employment_type, None)
        if contract:
            return contract
        if "ALTERNANCE" in title.upper() or "APPRENTISSAGE" in title.upper():
            return ContractType.INTERNSHIP
        return ContractType.CDI

    def get_experience(self, soup_job_level: BeautifulSoup, title: str) -> Experience:
        """Gets the job level from job page"""
        h3_tag = soup_job_level.find("h3", class_="description__job-criteria-subheader", string=lambda text: "Seniority level" in text)
        if not h3_tag:
            return BaseScraper.get_experience(self, title)
        job_level_span = h3_tag.find_next_sibling("span", class_=["description__job-criteria-text", "description__job-criteria-text--criteria"])
        if not job_level_span:
            return BaseScraper.get_experience(self, title)
        exp_str = job_level_span.get_text(strip=True)
        experience_map = {
            "Entry level": Experience.JUNIOR,
            "Executive": Experience.MID_LEVEL,
            "Mid-Senior level": Experience.EXPERIENCED,
            "Associate": Experience.SENIOR,
            "Internship": Experience.JUNIOR,
            "Director": Experience.SENIOR,
            "Not Applicable": None,
        }
        experience = experience_map.get(exp_str, None)
        if experience is None:
            return BaseScraper.get_experience(self, title)
        return experience

    def get_skills(self) -> list[str]:
        # TODO
        return []

    def get_salary(self, job_card: Tag) -> Salary | None:
        salary_tag = job_card.find("span", class_="job-search-card__salary-info")
        if not salary_tag:
            return None
        salary_text = salary_tag.get_text(separator=" ").strip()
        print(salary_text)
        salary_values = salary_text.split("-")
        salary_min = salary_values[0]
        salary_max = salary_values[1]
        currency = salary_text[0] if salary_text[0] != "$" else "USD"

        salary = Salary(
            min_amount=int(salary_min),
            max_amount=int(salary_max),
            currency=currency,
        )
        return salary

    def get_posted_date(self, metadata_card: Tag | None) -> datetime | None:
        datetime_tag = (
            metadata_card.find("time", class_="job-search-card__listdate")
            if metadata_card
            else None
        )
        if not datetime_tag and metadata_card:
            datetime_tag = metadata_card.find("time", class_="job-search-card__listdate--new")
        if datetime_tag and "datetime" in datetime_tag.attrs:
            datetime_str = str(datetime_tag["datetime"])
            try:
                return datetime.strptime(datetime_str, "%Y-%m-%d")
            except Exception as _:
                self.log.warning("Cannot parse datetime string")
                return None
        else:
            return None

    def get_address(self, metadata_card: Tag | None) -> str:
        """Extracts the location data from the job metadata card.
        :param metadata_card
        :return: str"""
        if metadata_card is None:
            return ""
        location_tag = metadata_card.find("span", class_="job-search-card__location")
        location_string = location_tag.text.strip() if location_tag else "N/A"
        parts = location_string.split(", ")
        if len(parts) > 0:
            return parts[0].title()
        else:
            return ""

    def get_company(self, company_a_tag: Tag | None) -> str:
        if company_a_tag:
            return company_a_tag.get_text(strip=True)
        return "N/A"

    def get_description(self, soup: BeautifulSoup) -> str:
        div_content = soup.find("div", class_=lambda x: x and "show-more-less-html__markup" in x)
        if div_content is None:
            return ""
        div_content = remove_attributes(div_content)
        description = div_content.prettify(formatter="html")
        # if self.scraper_input.description_format == FormatType.MARKDOWN:
        #     return markdown_converter(description)
        # else:
        #     return plain_converter(description)
        return markdown_converter(description)

    def get_title(self, job_card: Tag) -> str:
        title_tag = job_card.find("span", class_="sr-only")
        title = title_tag.get_text(strip=True) if title_tag else "N/A"
        return title

    def get_id(self, job_card: Tag) -> str:
        href_tag = job_card.find("a", class_="base-card__full-link")
        if href_tag and "href" in href_tag.attrs:
            href = href_tag.attrs["href"].split("?")[0]
            job_id = href.split("-")[-1]
            return f"li-{job_id}"
        return ""

def contract_type_code(contract_type: ContractType) -> str:
    contract_map = {
        ContractType.CDI: "F",
        ContractType.INTERIM: "P",
        ContractType.INTERNSHIP: "I",
        ContractType.OTHER: "C",
        ContractType.CDD: "T",
    }
    code = contract_map.get(contract_type, "")
    return code
