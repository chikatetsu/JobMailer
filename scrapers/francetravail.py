import re
import time
from datetime import datetime

import requests

from config import FRANCE_TRAVAIL_CLIENT_ID, FRANCE_TRAVAIL_API_KEY
from inputs.scraper_input import ScraperInput
from models.city import City
from models.contract_type import ContractType
from models.experience import Experience
from models.job import Job, JobReference
from models.job_response import JobResponse
from models.salary import Salary, SalaryPeriod
from scrapers.scraper import BaseScraper


class FranceTravail(BaseScraper):
    def __init__(self, city: City, scraper_input: ScraperInput, seen_jobs: set[str] | None = None):
        super().__init__(
            city=city,
            scraper_input=scraper_input,
            base_url="https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search",
            seen_jobs=seen_jobs,
        )

    @staticmethod
    def auth() -> str:
        token_response = requests.post(
            "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire",
            data={
                "grant_type": "client_credentials",
                "client_id": FRANCE_TRAVAIL_CLIENT_ID,
                "client_secret": FRANCE_TRAVAIL_API_KEY,
                "scope": "api_offresdemploiv2 o2dsoffre"
            }
        )
        token_response.raise_for_status()
        return token_response.json()["access_token"]

    @staticmethod
    def headers(access_token: str) -> dict:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        return headers

    def scrape(self) -> JobResponse:
        params = {
            # "accesTravailleurHandicape": "Not Set" | "False" | "True",
            # "appellation": 38444,
            # "codeNAF": "78.20Z",
            # "codeROME": "D1102,D1104,D1108",
            # "commune": "75001",
            "departement": self.city.value.city_code[:-3],
            # "region": "75",
            "distance": self.scraper_input.distance(),
            # "domaine": "G17",
            # "dureeContratMax": 24,
            # "dureeContratMin": 0.5,
            # "dureeHebdo": 1,
            # "dureeHebdoMax": 2430,
            # "dureeHebdoMin": 800,
            # "employeursHandiEngages": "Not Set" | "False" | "True",
            # "entreprisesAdaptees": "Not Set" | "False" | "True",
            # "experience": 2,
            # "experienceExigence": "D",
            # "grandDomaine": "M16",
            "inclureLimitrophes": "False", #"Not Set" | "False" | "True",
            # "maxCreationDate": "2022-04-15T07:18:25",
            # "minCreationDate": "2022-04-15T07:18:25",
            # "modeSelectionPartenaires": "INCLUS",
            "motsCles": self.scraper_input.search_term,
            # "natureContrat": "E1",
            # "niveauFormation": "NV3",
            # "offresMRS": "Not Set" | "False" | "True",
            # "offresManqueCandidats": "Not Set" | "False" | "True",
            # "origineOffre": 1,
            # "partenaires": "PARTENAIRE1",
            # "paysContinent": 99127,
            # "periodeSalaire": "M",
            # "permis": "B",
            # "publieeDepuis": 7,
            # "qualification": 9,
            # "salaireMin": 1400,
            # "secteurActivite": "01,02",
            # "sort": 1,
            # "tempsPlein": "Not Set" | "False" | "True",
            # "theme": 12,
            # "typeContrat": "CDI"
        }
        try:
            access_token = self.auth()
            headers = self.headers(access_token)
            jobs = []
            results = ["tmp"]
            i = 0
            while len(results) > 0:
                params["range"] = f"{i}-{i+149}"
                response = requests.get(self.base_url, headers=headers, params=params)
                if response.text == "":
                    break
                results = response.json().get("resultats", [])
                jobs.extend([self.process_job(res) for res in results])
                i += 150
                time.sleep(1)
            self.log.info("finished scraping")
            return JobResponse(jobs)
        except Exception as e:
            self.log.error(e)
            return JobResponse()

    def process_job(self, resp: dict) -> Job | JobReference:
        job_id = self.get_id(resp)
        if job_id in self.seen_jobs:
            return JobReference(job_id)

        description = self.get_description(resp)
        title = self.get_title(resp)
        job = Job(
            id=job_id,
            source=FranceTravail.__name__,
            title=title,
            description=description,
            company=self.get_company(resp),
            city=self.city,
            address=self.get_address(resp),
            posted_date=self.get_posted_date(resp),
            salary=self.get_salary(resp),
            skills=self.get_skills(resp),
            experience=self.get_experience(resp, title),
            remote_type=self.get_remote_type(description),
            contract_type=self.get_contract_type(resp, title),
            source_url=self.get_source_url(resp),
            real_url=self.get_real_url(),
            company_url=self.get_company_url(),
            company_logo=self.get_company_logo()
        )
        self.seen_jobs.add(job_id)
        return job

    def get_source_url(self, resp: dict) -> str:
        url = resp["origineOffre"]["urlOrigine"]
        return url

    def get_contract_type(self, resp: dict, title: str) -> ContractType:
        alternance = resp["alternance"]
        if alternance:
            return ContractType.INTERNSHIP

        job_type_str = resp["typeContrat"]
        map_job_type = {
            "CDI": ContractType.CDI,
            "CDD": ContractType.CDD,
            "MIS": ContractType.INTERIM,
            "SAI": ContractType.SEASON,
            "CCE": ContractType.OTHER,
            "FRA": ContractType.OTHER,
            "LIB": ContractType.OTHER,
            "REP": ContractType.OTHER,
            "TTI": ContractType.CDD,
            "DDI": ContractType.CDD,
            "DIN": ContractType.INTERIM,
            "DDT": ContractType.CDD
        }
        contract_type = map_job_type.get(job_type_str, None)
        if contract_type is not None:
            return contract_type
        if "alternance" in title.lower() or "apprentissage" in title.lower():
            return ContractType.INTERNSHIP
        return ContractType.CDI

    def get_experience(self, resp: dict, title: str) -> Experience:
        experience_raw = resp["experienceLibelle"] # = 5 An(s)
        if experience_raw == "Débutant accepté":
            return Experience.JUNIOR
        elif experience_raw == "Expérience exigée":
            return Experience.MID_LEVEL
        if " Mois" in experience_raw:
            years_required = int(float(experience_raw.split(" ")[0]) / 12)
            return Experience.from_years_required(years_required)
        if " An(s)" in experience_raw:
            years_required = int(experience_raw.split(" ")[0])
            return Experience.from_years_required(years_required)
        return BaseScraper.get_experience(self, title)

    def get_skills(self, resp: dict) -> list[str]:
        languages = [language["libelle"] for language in resp.get("langues", [])]
        competences = [language["libelle"] for language in resp.get("competences", [])]
        skills = competences + languages
        return skills

    def get_salary(self, resp: dict) -> Salary | None:
        salary = resp["salaire"].get("libelle", "")
        if salary == "":
            salary = resp["salaire"].get("commentaire", "")
            if salary == "":
                return None

        pattern = r"(?P<period>Annuel|Mensuel)\s+de\s+(?P<min>\d+(?:\.\d+)?)\s+Euros\s+à\s+(?P<max>\d+(?:\.\d+)?)"
        match = re.search(pattern, salary)
        if not match:
            return None
        period = match.group("period")
        min_amount = int(float(match.group("min")))
        max_amount = int(float(match.group("max")))
        if period == "Annuel":
            return Salary.from_raw(min_amount, max_amount, SalaryPeriod.YEARLY)
        elif period == "Mensuel":
            return Salary.from_raw(min_amount, max_amount, SalaryPeriod.MONTHLY)
        return None

    def get_posted_date(self, resp: dict) -> datetime | None:
        if "dateCreation" not in resp:
            return None
        posted_date_raw = resp["dateCreation"]
        posted_date = datetime.fromisoformat(posted_date_raw.replace("Z", "+00:00"))
        return posted_date

    def get_address(self, resp) -> str:
        city = resp["lieuTravail"]["libelle"]
        city_splitted = city.split(" - ")
        if len(city_splitted) > 1:
            city = " - ".join(city_splitted[1:])
        city.lower().title()
        cp = resp["lieuTravail"].get("codePostal", "")
        if cp == "":
            cp = resp["lieuTravail"].get("commune", "")
        if cp != "":
            address = f"{cp} {city}"
        else:
            address = city
        return address

    def get_company(self, resp: dict) -> str:
        company = resp["entreprise"].get("nom", "")
        if company == "":
            company_description = resp["entreprise"].get("description", "")
            if company_description != "":
                company = company_description.strip().split(" est ")[0]
        return company

    def get_description(self, resp: dict) -> str:
        description = resp["description"].replace("L'entreprise accompagnée et les missions:", "").strip()
        return description

    def get_title(self, resp: dict) -> str:
        title = resp["intitule"]
        return title

    def get_id(self, resp: dict) -> str:
        job_id = resp["id"]
        return f"fr_{job_id}"

    def get_company_logo(self) -> str:
        return "https://www.francetravail.fr/logos/img/partenaires/francetravail.svg"

    def get_company_url(self) -> str:
        # TODO
        return ""

    def get_real_url(self) -> str:
        # TODO
        return ""