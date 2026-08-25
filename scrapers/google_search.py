import json
import re
from datetime import datetime, timedelta

import requests

from inputs.scraper_input import ScraperInput
from models.city import City
from models.contract_type import ContractType
from models.job import Job, JobReference
from models.job_response import JobResponse
from models.salary import Salary
from scrapers.scraper import BaseScraper, SessionScraper


class GoogleSearch(BaseScraper, SessionScraper):
    def __init__(self, city: City, scraper_input: ScraperInput, seen_jobs: set[str] | None = None, proxies: list[str] | str | None = None, ca_cert: str | None = None):
        BaseScraper.__init__(self, city, scraper_input, "https://www.google.com/search", seen_jobs=seen_jobs)
        SessionScraper.__init__(self, proxies, ca_cert)
        self.jobs_per_page = 10
        self.jobs_url = "https://www.google.com/async/callback:550"
        self.headers_initial = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "priority": "u=0, i",
            "referer": "https://www.google.com/",
            "sec-ch-prefers-color-scheme": "dark",
            "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
            "sec-ch-ua-arch": '"arm"',
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-form-factors": '"Desktop"',
            "sec-ch-ua-full-version": '"130.0.6723.58"',
            "sec-ch-ua-full-version-list": '"Chromium";v="130.0.6723.58", "Google Chrome";v="130.0.6723.58", "Not?A_Brand";v="99.0.0.0"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"macOS"',
            "sec-ch-ua-platform-version": '"15.0.1"',
            "sec-ch-ua-wow64": "?0",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "x-browser-channel": "stable",
            "x-browser-copyright": "Copyright 2024 Google LLC. All rights reserved.",
            "x-browser-year": "2024",
        }
        self.headers_jobs = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "priority": "u=1, i",
            "referer": "https://www.google.com/",
            "sec-ch-prefers-color-scheme": "dark",
            "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
            "sec-ch-ua-arch": '"arm"',
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-form-factors": '"Desktop"',
            "sec-ch-ua-full-version": '"130.0.6723.58"',
            "sec-ch-ua-full-version-list": '"Chromium";v="130.0.6723.58", "Google Chrome";v="130.0.6723.58", "Not?A_Brand";v="99.0.0.0"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"macOS"',
            "sec-ch-ua-platform-version": '"15.0.1"',
            "sec-ch-ua-wow64": "?0",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        }

    def scrape(self) -> JobResponse:
        forward_cursor, job_list = self._get_initial_cursor_and_jobs()
        page = 1

        while forward_cursor:
            self.log.info(f"search page: {page}")
            try:
                jobs, forward_cursor = self._get_jobs_next_page(forward_cursor)
            except Exception as e:
                self.log.error(f"failed to get jobs on page: {page}, {e}")
                break
            if not jobs:
                self.log.info(f"found no jobs on page: {page}")
                break
            job_list += jobs
            page += 1
        self.log.info("finished scraping")
        return JobResponse(job_list)

    def _get_jobs_next_page(self, forward_cursor: str) -> tuple[list[Job], str]:
        params = {"fc": [forward_cursor], "fcv": ["3"], "async": ["_basejs:/xjs/_/js/k=xjs.s.en_US.JwveA-JiKmg.2018.O/am=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAAAAAAAACAAAoICAAAAAAAKMAfAAAAIAQAAAAAAAAAAAAACCAAAEJDAAACAAAAAGABAIAAARBAAABAAAAAgAgQAABAASKAfv8JAAABAAAAAAwAQAQACQAAAAAAcAEAQABoCAAAABAAAIABAACAAAAEAAAAFAAAAAAAAAAAAAAAAAAAAAAAAACAQADoBwAAAAAAAAAAAAAQBAAAAATQAAoACOAHAAAAAAAAAQAAAIIAAAA_ZAACAAAAAAAAcB8APB4wHFJ4AAAAAAAAAAAAAAAACECCYA5If0EACAAAAAAAAAAAAAAAAAAAUgRNXG4AMAE/dg=0/br=1/rs=ACT90oGxMeaFMCopIHq5tuQM-6_3M_VMjQ,_basecss:/xjs/_/ss/k=xjs.s.IwsGu62EDtU.L.B1.O/am=QOoQIAQAAAQAREADEBAAAAAAAAAAAAAAAAAAAAAgAQAAIAAAgAQAAAIAIAIAoEwCAADIC8AfsgEAawwAPkAAjgoAGAAAAAAAAEADAAAAAAIgAECHAAAAAAAAAAABAQAggAARQAAAQCEAAAAAIAAAABgAAAAAIAQIACCAAfB-AAFIQABoCEA_CgEAAIABAACEgHAEwwAEFQAM4CgAAAAAAAAAAAAACABCAAAAQEAAABAgAMCPAAA4AoE2BAEAggSAAIoAQAAAAAgAAAAACCAQAAAxEwA_ZAACAAAAAAAAAAkAAAAAAAAgAAAAAAAAAAAAAAAAAAAAAAAAQAEAAAAAAAAAAAAAAAAAAAAAQA/br=1/rs=ACT90oGZc36t3uUQkj0srnIvvbHjO2hgyg,_basecomb:/xjs/_/js/k=xjs.s.en_US.JwveA-JiKmg.2018.O/ck=xjs.s.IwsGu62EDtU.L.B1.O/am=QOoQIAQAAAQAREADEBAAAAAAAAAAAAAAAAAAAAAgAQAAIAAAgAQAAAKAIAoIqEwCAADIK8AfsgEAawwAPkAAjgoAGAAACCAAAEJDAAACAAIgAGCHAIAAARBAAABBAQAggAgRQABAQSOAfv8JIAABABgAAAwAYAQICSCAAfB-cAFIQABoCEA_ChEAAIABAACEgHAEwwAEFQAM4CgAAAAAAAAAAAAACABCAACAQEDoBxAgAMCPAAA4AoE2BAEAggTQAIoASOAHAAgAAAAACSAQAIIxEwA_ZAACAAAAAAAAcB8APB4wHFJ4AAAAAAAAAAAAAAAACECCYA5If0EACAAAAAAAAAAAAAAAAAAAUgRNXG4AMAE/d=1/ed=1/dg=0/br=1/ujg=1/rs=ACT90oFNLTjPzD_OAqhhtXwe2pg1T3WpBg,_fmt:prog,_id:fc_5FwaZ86OKsfdwN4P4La3yA4_2"]}
        response = self.session.get(self.jobs_url, headers=self.headers_jobs, params=params)
        return self._parse_jobs(response.text)

    def _parse_jobs(self, job_data: str) -> tuple[list[Job], str]:
        start_idx = job_data.find("[[[")
        end_idx = job_data.rindex("]]]") + 3
        s = job_data[start_idx:end_idx]
        parsed = json.loads(s)[0]

        pattern_fc = r'data-async-fc="([^"]+)"'
        match_fc = re.search(pattern_fc, job_data)
        data_async_fc = match_fc.group(1) if match_fc else None
        jobs_on_page = []
        for array in parsed:
            _, job_data = array
            if not job_data.startswith("[[["):
                continue
            job_d = json.loads(job_data)

            job_info = self.find_job_info(job_d)
            job_post = self.process_job(job_info)
            if job_post:
                jobs_on_page.append(job_post)
        return jobs_on_page, data_async_fc

    def process_job(self, job_info: dict) -> Job | JobReference | None:
        job_id = self.get_id(job_info)
        if job_id in self.seen_jobs:
            return JobReference(job_id)

        source_url = self.get_source_url(job_info)
        description = self.get_description(job_info)
        title = self.get_title(job_info)

        job = Job(
            id=job_id,
            source=GoogleSearch.__name__,
            title=title,
            description=description,
            company=self.get_company(job_info),
            city=self.city,
            address=self.get_address(job_info),
            posted_date=self.get_posted_date(job_info),
            salary=self.get_salary(),
            skills=self.get_skills(),
            experience=self.get_experience(title),
            remote_type=self.get_remote_type(description),
            contract_type=self.get_contract_type(),
            source_url=source_url,
            real_url=self.get_real_url(),
            company_url=self.get_company_url(),
            company_logo=self.get_company_logo()
        )
        self.seen_jobs.add(job_id)
        return job

    def _get_initial_cursor_and_jobs(self) -> tuple[int, list[Job | JobReference]]:
        query = f"{self.scraper_input.search_term} jobs near {self.city}"
        params = {"q": query, "udm": "8"}
        try:
            response = requests.get(self.base_url, headers=self.headers_initial, params=params)

            pattern_fc = r'<div jsname="Yust4d"[^>]+data-async-fc="([^"]+)"'
            match_fc = re.search(pattern_fc, response.text)
            if match_fc:
                data_async_fc = match_fc.group(1)
            else:
                self.log.error(f"failed to get data_async_fc")
                data_async_fc = None
            jobs_raw = self.find_job_info_initial_page(response.text)
            jobs = []
            for job_raw in jobs_raw:
                job = self.process_job(job_raw)
                if job:
                    jobs.append(job)
            return data_async_fc, jobs
        except Exception as e:
            self.log.error(f"failed to get jobs: {e}")

    def find_job_info_initial_page(self, html_text: str):
        pattern = r'520084652":("\[.*?\]\s*])\s*}\s*]\s*]\s*]\s*]\s*]'
        results = []
        matches = re.finditer(pattern, html_text)
        for match in matches:
            try:
                parsed_data = json.loads(match.group(1))
                results.append(parsed_data)
            except json.decoder.JSONDecodeError as e:
                self.log.error(f"Failed to parse match: {e}")
                results.append({"raw_match": match.group(0), "error": str(e)})
        return results

    def find_job_info(self, jobs_data: list | dict) -> list | None:
        if isinstance(jobs_data, dict):
            for key, value in jobs_data.items():
                if key == "520084652" and isinstance(value, list):
                    return value
                else:
                    result = self.find_job_info(value)
                    if result:
                        return result
        elif isinstance(jobs_data, list):
            for item in jobs_data:
                result = self.find_job_info(item)
                if result:
                    return result
        return None

    @staticmethod
    def _get_time_range(hours_old) -> str:
        if hours_old <= 24:
            return "since yesterday"
        elif hours_old <= 72:
            return "in the last 3 days"
        elif hours_old <= 168:
            return "in the last week"
        else:
            return "in the last month"

    def get_id(self, job_info) -> str:
        job_id = f"go-{job_info[28]}"
        return job_id

    def get_title(self, job_info) -> str:
        title = job_info[0]
        return title

    def get_description(self, job_info) -> str:
        description = job_info[19]
        return description

    def get_company(self, job_info) -> str:
        company_name = job_info[1]
        return company_name

    def get_address(self, job_info) -> str:
        location = job_info[2]
        if location and "," in location:
            splitted = location.split(",")
            city = splitted[0].strip()
        else:
            city = location
        return city.title()

    def get_posted_date(self, job_info) -> datetime | None:
        days_ago_str = job_info[12]
        if type(days_ago_str) != str:
            return None
        match = re.search(r"\d+", days_ago_str)
        if not match:
            return None
        days_ago = float(match.group())
        date_posted = datetime.now() - timedelta(days=days_ago)
        return date_posted

    def get_salary(self, **kwargs) -> Salary | None:
        pass

    def get_skills(self, **kwargs) -> list[str]:
        pass

    def get_contract_type(self, **kwargs) -> ContractType:
        pass

    def get_source_url(self, job_info) -> str:
        url = job_info[3][0][0] if job_info[3] and job_info[3][0] else ""
        return url

    def get_real_url(self, **kwargs) -> str:
        pass

    def get_company_url(self, **kwargs) -> str:
        pass

    def get_company_logo(self, **kwargs) -> str:
        pass
