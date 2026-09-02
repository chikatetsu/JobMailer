import json
import sys
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode, quote

from bs4 import BeautifulSoup, Tag

from inputs.scraper_input import ScraperInput
from models.city import City
from models.contract_type import ContractType
from models.experience import Experience
from models.job import Job, JobReference
from models.job_response import JobResponse
from models.remote_type import RemoteType
from models.salary import Salary, SalaryPeriod
from .scraper import BaseScraper, SessionScraper


class Tekkit(BaseScraper, SessionScraper):
    def __init__(self, city: City, scraper_input: ScraperInput, seen_jobs: set[str] | None = None, proxies: list[str] | str | None = None, ca_cert: str | None = None):
        BaseScraper.__init__(self, city,  scraper_input, "https://tekkit.io", seen_jobs=seen_jobs)
        SessionScraper.__init__(self, proxies, ca_cert)
        self.location_data = self._get_location_data()

    def _build_url(self, page: int) -> str:
        """Construit l'URL Tekkit à partir d'un mot-clé et d'une ville"""
        params = {
            "search": self.scraper_input.search_term,
            "loc": self.location_data,
            "rayon": self.scraper_input.distance([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160]),
            "page": page
        }
        return f"{self.base_url}/offres?{urlencode(params, quote_via=quote)}"

    def _get_location_data(self) -> dict[Any, Any] | str | None:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": f"{self.city}, France",
            "format": "json",
            "addressdetails": 1,
            "limit": 1
        }
        headers = {"User-Agent": "TekktitScraper/1.0 (contact@monmail.com)"}

        try:
            r = self.session.get(url, params=params, headers=headers)
            r.raise_for_status()
            results = r.json()

            if not results:
                self.log.error(f"Ville '{self.city}' introuvable. Impossible de la géocoder")
                return None

            addr = results[0].get("address", {})
            formatted = {
                "typeOfLocation": "locality",
                "formatted_address": f"{self.city}, France",
                "address": "",
                "city": addr.get("city") or addr.get("town") or addr.get("village") or str(self.city),
                "dep": addr.get("county", ""),
                "region": addr.get("state", ""),
                "zip": "",
                "country": "France",
                "lng": float(results[0]["lon"]),
                "lat": float(results[0]["lat"])
            }
            return json.dumps([formatted], ensure_ascii=False, separators=(',', ':'))
        except Exception as e:
            self.log.error(f"Cannot geocode city '{self.city}' : {e}")
            return None

    def scrape(self) -> JobResponse:
        if not self.location_data:
            return JobResponse()
        jobs = []
        try:
            for page in range(1, sys.maxsize):
                url = self._build_url(page)
                self.log.info(f"scraping page {page}...")
                response = self.session.get(url)
                soup = BeautifulSoup(response.text, "html.parser")

                job_cards = soup.select("div:has(h3 a[href^='/offre/'])")
                for card in job_cards:
                    job = self.process_job(card)
                    if job is not None:
                        jobs.append(job)

                next_button = soup.find("button", class_=["button-outline", "button-full-width"])
                if next_button and next_button.get_text(strip=True) == "Page précédente":
                    self.log.info("finished scrapping")
                    break
        except Exception as e:
            self.log.error(e)
        return JobResponse(jobs)

    def process_job(self, job_card: Tag) -> Job | JobReference | None:
        link = job_card.find("a")
        job_id = self.get_id(link)
        if job_id == "":
            return None
        if job_id in self.seen_jobs:
            return JobReference(job_id)

        source_url = self.get_source_url(link)
        if source_url == "https://tekkit.io/offres":
            return None
        job_page = self.session.get(source_url)
        more_soup = BeautifulSoup(job_page.text, "html.parser")
        raw_json = more_soup.find("script", id="__NEXT_DATA__")

        json_data = json.loads(raw_json.get_text(strip=True)) if raw_json else ""
        props = json_data["props"]['initialProps']["pageProps"]["offreSSR"]

        title = self.get_title(props)
        if title == "":
            return None

        job = Job(
            id=job_id,
            source=Tekkit.__name__,
            title=title,
            description=self.get_description(props),
            company=self.get_company(props),
            city=self.city,
            address=self.get_address(props),
            posted_date=self.get_posted_date(job_card),
            salary=self.get_salary(props),
            skills=self.get_skills(props),
            experience=self.get_experience(props, title),
            remote_type=self.get_remote_type(props),
            contract_type=self.get_contract_type(props),
            source_url=source_url,
            real_url=self.get_real_url(props),
            company_url=self.get_company_url(),
            company_logo=self.get_company_logo(props)
        )
        self.seen_jobs.add(job_id)
        return job

    def get_id(self, link: Tag | None) -> str:
        if not link:
            return ""
        url = link.get("href", "")
        if url == "":
            return ""
        raw_id = str(url).replace("/offre/", "").replace("/", "_")
        return f"tk_{raw_id}"

    def get_title(self, json_data: dict) -> str:
        title = json_data.get("titre", "")
        return title

    def get_description(self, json_data: dict) -> str:
        desc_entreprise_raw = json_data.get("descEntreprise", "")
        missions_raw = json_data.get("missions", "")
        profil_raw = json_data.get("profil", "")
        desc_entreprise = desc_entreprise_raw if desc_entreprise_raw else ""
        missions = missions_raw if missions_raw else ""
        profil = profil_raw if profil_raw else ""
        desc_raw = desc_entreprise + missions + profil
        parsed = BeautifulSoup(desc_raw, "html.parser")
        description = parsed.get_text(strip=True)
        return description

    def get_company(self, job_json: dict) -> str:
        # company_raw = job_card.find("strong")
        # if not company_raw:
        #     return ""
        # company = company_raw.get_text(strip=True)
        company = job_json.get("auteur", {}).get("nom", "")
        return company

    def get_address(self, json_data: dict) -> str:
        address = json_data.get("address", "")
        if address == "":
            address = json_data.get("ville", {}).get("nom", "")
        return address.title()

    def get_posted_date(self, job_card: Tag) -> datetime | None:
        date_raw = job_card.find("div", class_=["hidden", "mt-1", "text-base", "md:block", "text-gray40"])
        if not date_raw:
            return datetime.now()

        if date_raw.startwith("Le "):
            day, month, year = date_raw.replace("Le ", "").split("/")
            return datetime(int(year), int(month), int(day))
        elif date_raw.startwith("Il y a "):
            day = int(date_raw.replace("Il y a ", "").replace(" jours", "").replace(" jour", ""))
            return datetime.now() - timedelta(days=day)

        self.log.debug(date_raw)
        # TODO
        return None

    def get_salary(self, job_json: dict) -> Salary | None:
        remuneration = job_json.get("remuneration", {})
        min_salary = remuneration.get("min", None)
        max_salary = remuneration.get("max", None)
        type_salary = remuneration.get("type", "")
        period_map = {
            "ANNUEL": SalaryPeriod.YEARLY,
            "MENSUEL": SalaryPeriod.MONTHLY,
        }
        period_salary = period_map.get(type_salary, None)
        if min_salary and max_salary and period_salary:
            return Salary.from_raw(float(min_salary), float(max_salary), period_salary)
        return None

    def get_skills(self, job_json: dict) -> list[str]:
        skills_raw = job_json.get("competences", [])
        skills = [skill.get("nom", "") for skill in skills_raw]
        return skills

    def get_experience(self, job_json: dict, title: str) -> Experience:
        # if not infos or len(infos) < 2:
        #     return BaseScraper.get_experience(self, title)
        # exp_str = infos[1].get_text(strip=True)
        # exp_map = {
        #     "Junior (- de 3 ans)": Experience.JUNIOR,
        #     "Expert 8 ans et +": Experience.SENIOR,
        #     "Expérimenté (+ de 3 ans)": Experience.MID_LEVEL
        # }
        # experience = exp_map.get(exp_str, None)
        xp = job_json.get("xp", "")
        xp_map = {
            "0": Experience.JUNIOR,
            "3ANSMOINS": Experience.JUNIOR,
            "3ANSPLUS": Experience.MID_LEVEL,
            "8ANSPLUS": Experience.SENIOR
        }
        experience = xp_map.get(xp, None)
        if experience is None:
            return BaseScraper.get_experience(self, title)
        return experience

    def get_remote_type(self, json_data: dict) -> RemoteType:
        remote_raw = json_data.get("isAvailableRemoteWork", False)
        remote_type = RemoteType.REMOTE if bool(remote_raw) else RemoteType.ON_SITE
        return remote_type

    def get_contract_type(self, json_data: dict) -> ContractType:
        contract = json_data.get("contract", "")
        contract_map = {
            "CDI": ContractType.CDI,
            "CDD": ContractType.CDD,
            "Stage": ContractType.INTERNSHIP,
            "Intérim": ContractType.INTERIM,
            "Alternance": ContractType.INTERNSHIP,
            "Indépendant": ContractType.OTHER,
            "VIE": ContractType.OTHER,
        }
        return contract_map.get(contract, ContractType.CDI)

    def get_source_url(self, link: Tag | None) -> str:
        if not link:
            return ""
        url = link.get("href", "")
        if url == "":
            return ""
        return f"{self.base_url}{url}"

    def get_real_url(self, json_data: dict) -> str:
        real_url = json_data.get("urlCandid", "").replace("?source=tekkit", "")
        return real_url

    def get_company_url(self) -> str:
        # TODO
        return ""

    def get_company_logo(self, job_json: dict) -> str:
        default = "https://cdn.carrevolutis.com/reborn-production-cdn-bucket/societes/20/tekkit-io_n.png"
        # logo_raw = job_card.find("img")
        # if not logo_raw:
        #     return default
        # logo = str(logo_raw.get("src", default))
        logo = job_json.get("auteur", {}).get("logo", {}).get("mini", default)
        return logo
