import random
from abc import abstractmethod, ABC
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from config import FIREFOX_PATH
from inputs.scraper_input import ScraperInput
from models.city import City
from models.contract_type import ContractType
from models.experience import Experience
from models.job import Job, JobReference
from models.job_response import JobResponse
from models.remote_type import RemoteType
from models.salary import Salary
from utils.logger import create_logger
from utils.util import create_session


class SessionScraper:
    def __init__(self, proxies: list[str] | str | None = None, ca_cert: str | None = None):
        self.session = create_session(
            proxies=proxies,
            ca_cert=ca_cert,
            is_tls=False,
            has_retry=True,
            delay=5,
            clear_cookies=True,
        )

class SeleniumScraper:
    def __init__(self):
        self.driver = self._init_driver()

    @staticmethod
    def _init_driver(headless: bool = True) -> webdriver.Firefox:
        options = Options()
        options.binary_location = FIREFOX_PATH
        if headless:
            options.add_argument('--headless=new')
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference(
            "general.useragent.override",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0"
        )
        driver = webdriver.Firefox(options=options)
        return driver

class BaseScraper(ABC):
    def __init__(self, city: City, scraper_input: ScraperInput, base_url: str, seen_jobs: set[str] | None = None):
        self.city = city
        self.scraper_input = scraper_input
        self.base_url = base_url
        self.seen_jobs = seen_jobs if seen_jobs else set()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.log = create_logger(cls.__name__)

    @abstractmethod
    def scrape(self) -> JobResponse: ...

    @staticmethod
    def _random_delay(min_s=1.5, max_s=4.0):
        return random.uniform(min_s, max_s)

    @abstractmethod
    def process_job(self, **kwargs) -> Job | JobReference: ...

    @abstractmethod
    def get_id(self, **kwargs) -> str: ...

    @abstractmethod
    def get_title(self, **kwargs) -> str: ...

    @abstractmethod
    def get_description(self, **kwargs) -> str: ...

    @abstractmethod
    def get_company(self, **kwargs) -> str: ...

    @abstractmethod
    def get_address(self, **kwargs) -> str: ...

    @abstractmethod
    def get_posted_date(self, **kwargs) -> datetime | None: ...

    @abstractmethod
    def get_salary(self, **kwargs) -> Salary | None: ...

    @abstractmethod
    def get_skills(self, **kwargs) -> list[str]: ...

    def get_experience(self, title: str) -> Experience:
        title = title.lower()
        if "senior" in title:
            return Experience.SENIOR
        elif "sénior" in title:
            return Experience.SENIOR
        elif "junior" in title:
            return Experience.JUNIOR
        elif "confirmé" in title:
            return Experience.MID_LEVEL
        elif "lead" in title:
            return Experience.EXPERIENCED
        else:
            return Experience.MID_LEVEL

    def get_remote_type(self, text: str) -> RemoteType:
        remote_keywords = {"remote", "work from home", "wfh", "distanciel"}
        hybrid_keywords = {"hybrid", "télétravail", "télé-travail"}
        formatted = text.lower()
        if any(keyword in formatted for keyword in remote_keywords):
            return RemoteType.REMOTE
        if any(keyword in formatted for keyword in hybrid_keywords):
            return RemoteType.HYBRID
        return RemoteType.ON_SITE

    @abstractmethod
    def get_contract_type(self, **kwargs) -> ContractType: ...

    @abstractmethod
    def get_source_url(self, **kwargs) -> str: ...

    @abstractmethod
    def get_real_url(self, **kwargs) -> str: ...

    @abstractmethod
    def get_company_url(self, **kwargs) -> str: ...

    @abstractmethod
    def get_company_logo(self, **kwargs) -> str: ...
