from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from inputs.scraper_config import ScraperConfig
from inputs.scraper_input import ScraperInput
from models.job_response import JobResponse
from models.site import Site
from scrapers.bayt import BaytScraper
from scrapers.francetravail import FranceTravail
from scrapers.glassdoor import Glassdoor
from scrapers.google_search import GoogleSearch
from scrapers.hellowork import HelloWork
from scrapers.indeed import Indeed
from scrapers.linkedin import LinkedIn
from scrapers.scraper import SessionScraper, BaseScraper
from scrapers.tekkit import Tekkit
from scrapers.welcometothejungle import WelcomeToTheJungle
from scrapers.ziprecruiter import ZipRecruiter
from .logger import set_logger_level


MAP_SCRAPER_SITE: dict[Site, type[BaseScraper]] = {
    Site.LINKEDIN: LinkedIn,
    Site.INDEED: Indeed,
    Site.ZIP_RECRUITER: ZipRecruiter,
    Site.GLASSDOOR: Glassdoor,
    Site.GOOGLE: GoogleSearch,
    Site.BAYT: BaytScraper,
    Site.FRANCE_TRAVAIL: FranceTravail,
    Site.HELLOWORK: HelloWork,
    Site.TEKKIT: Tekkit,
    Site.WELCOME_TO_THE_JUNGLE: WelcomeToTheJungle
}

def scrape_jobs(scraper_input: ScraperInput, scraper_config: ScraperConfig, seen_jobs: set[str] | None = None) -> JobResponse:
    set_logger_level(scraper_config.verbose)

    def scrape_site(scraper_class: type[BaseScraper]) -> JobResponse:
        all_city_data = JobResponse()
        for city in scraper_input.cities:
            if issubclass(scraper_class, SessionScraper):
                scraper = scraper_class(city=city, scraper_input=scraper_input, seen_jobs=seen_jobs, proxies=scraper_config.proxies, ca_cert=scraper_config.ca_cert)
            else:
                scraper = scraper_class(city=city, scraper_input=scraper_input, seen_jobs=seen_jobs)
            scraped_data: JobResponse = scraper.scrape()
            all_city_data += scraped_data
        return all_city_data

    job_response = JobResponse()
    with ThreadPoolExecutor() as executor:
        future_to_site = {
            executor.submit(scrape_site, MAP_SCRAPER_SITE[site]): site for site in scraper_config.websites
        }
        for future in as_completed(future_to_site):
            scraped_data = future.result()
            job_response += scraped_data
    return job_response
