from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import requests

from inputs.scraper_input import ScraperInput
from models.city import City
from models.contract_type import ContractType
from models.job import Job, JobReference
from models.job_response import JobResponse
from models.remote_type import RemoteType
from models.salary import Salary, SalaryPeriod
from scrapers.scraper import BaseScraper, SessionScraper
from utils.util import markdown_converter


class Glassdoor(BaseScraper, SessionScraper):
    def __init__(self, city: City, scraper_input: ScraperInput, seen_jobs: set[str] | None = None, proxies: list[str] | str | None = None, ca_cert: str | None = None):
        BaseScraper.__init__(self, city=city, scraper_input=scraper_input, base_url="https://www.glassdoor.fr/", seen_jobs=seen_jobs)
        SessionScraper.__init__(self, proxies, ca_cert)
        token = self._get_csrf_token()
        self.headers = {
            "authority": "www.glassdoor.fr", "accept": "*/*", "accept-language": "en-US,en;q=0.9",
            "apollographql-client-name": "job-search-next", "apollographql-client-version": "4.65.5",
            "content-type": "application/json", "origin": "https://www.glassdoor.fr",
            "referer": "https://www.glassdoor.fr/",
            "sec-ch-ua": '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
            "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"macOS"', "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "gd-csrf-token": token if token else "Ft6oHEWlRZrxDww95Cpazw:0pGUrkb2y3TyOpAIqF2vbPmUXoXVkD3oEGDVkvfeCerceQ5-n8mBg3BovySUIjmCPHCaW0H2nQVdqzbtsYqf4Q:wcqRqeegRUa9MVLJGyujVXB7vWFPjdaS1CtrrzJq-ok"
        }
        self.session.headers.update(self.headers)
        self.jobs_per_page = 30
        self.max_pages = 30


    def scrape(self) -> JobResponse:
        """
        Scrapes Glassdoor for jobs with scraper_input criteria.
        :return: JobResponse containing a list of jobs.
        """
        location_id, location_type = self._format_location(str(self.city))
        if location_type is None:
            self.log.error("Glassdoor: location not parsed")
            return JobResponse()
        job_list: list[Job | JobReference] = []
        cursor = None

        range_start = 1
        for page in range(range_start, sys.maxsize):
            self.log.info(f"search page: {page}")
            try:
                jobs, cursor = self._fetch_jobs_page(
                    self.scraper_input, location_id, location_type, page, cursor
                )
                job_list.extend(jobs)
                if not jobs:
                    break
            except Exception as e:
                self.log.error(f"Glassdoor: {e}")
                break
        self.log.info("finished scraping")
        return JobResponse(job_list)

    def get_id(self, job_data: dict) -> str:
        job_id = job_data["jobview"]["job"]["listingId"]
        return job_id

    def get_source(self) -> str:
        pass

    def get_title(self, job: dict) -> str:
        title = job["job"]["jobTitleText"]
        return title

    def get_description(self, job_id: str) -> str:
        url = f"{self.base_url}/graph"
        body = [
            {
                "operationName": "JobDetailQuery",
                "variables": {
                    "jl": job_id,
                    "queryString": "q",
                    "pageTypeEnum": "SERP",
                },
                "query": """
                        query JobDetailQuery($jl: Long!, $queryString: String, $pageTypeEnum: PageTypeEnum) {
                            jobview: jobView(
                                listingId: $jl
                                contextHolder: {queryString: $queryString, pageTypeEnum: $pageTypeEnum}
                            ) {
                                job {
                                    description
                                    __typename
                                }
                                __typename
                            }
                        }
                        """,
            }
        ]
        try:
            res = requests.post(url, json=body, headers=self.headers)
            if res.status_code != 200:
                return ""
            data = res.json()[0]
            desc = data["data"]["jobview"]["job"]["description"]
            # if self.scraper_input.description_format == FormatType.MARKDOWN:
            desc = markdown_converter(desc)
            return desc
        except Exception as e:
            self.log.error(f"Failed to fetch job description for job {job_id}: {e}")
            return ""

    def get_company(self, job_view: dict) -> str:
        company_name = job_view["header"]["employerNameFromSearch"]
        return company_name

    def get_address(self, job_view: dict, remote_type: RemoteType) -> str:
        if remote_type == RemoteType.REMOTE:
            return ""
        location_name = job_view["header"].get("locationName", "")
        if not location_name or location_name == "Remote":
            return ""
        city, _, _ = location_name.partition(", ")
        return city.title()

    def get_posted_date(self, job_view: dict) -> datetime | None:
        age_in_days = job_view["header"].get("ageInDays")
        if age_in_days is None:
            return None
        date_diff = (datetime.now() - timedelta(days=age_in_days))
        return date_diff

    def get_salary(self, data: dict) -> Salary | None:
        header = data.get("header")
        if header is None:
            return None
        pay_period = header.get("payPeriod")
        adjusted_pay = header.get("payPeriodAdjustedPay")
        currency = header.get("payCurrency", "USD")
        if not pay_period or not adjusted_pay:
            return None

        period = SalaryPeriod.from_string(str(pay_period))
        min_amount = int(adjusted_pay.get("p10") // 1)
        max_amount = int(adjusted_pay.get("p90") // 1)
        return Salary.from_raw(min_amount, max_amount, period, currency)

    def get_skills(self) -> list[str]:
        # TODO
        return []

    def get_remote_type(self, job_view: dict) -> RemoteType:
        type_raw = job_view["header"].get("locationType", "")
        if type_raw == "S":
            return RemoteType.REMOTE
        return RemoteType.ON_SITE

    def get_contract_type(self) -> ContractType:
        # TODO
        return ContractType.CDI

    def get_source_url(self, job_id: str) -> str:
        source_url = f"{self.base_url}job-listing/j?jl={job_id}"
        return source_url

    def get_real_url(self) -> str:
        # TODO
        return ""

    def get_company_url(self, job_view: dict) -> str:
        company_id = job_view["header"]["employer"]["id"]
        company_url = f"{self.base_url}Overview/W-EI_IE{company_id}.htm"
        return company_url

    def get_company_logo(self, job_data: dict) -> str:
        logo = job_data.get("overview", {}).get("squareLogoUrl", "")
        return logo

    def _fetch_jobs_page(
        self,
        scraper_input: ScraperInput,
        location_id: int,
        location_type: str,
        page_num: int,
        cursor: str | None,
    ) -> tuple[list[Job | JobReference], str | None]:
        """
        Scrapes a page of Glassdoor for jobs with scraper_input criteria
        """
        jobs: list[Job | JobReference] = []
        self.scraper_input = scraper_input
        try:
            payload = self._add_payload(location_id, location_type, page_num, cursor)
            response = self.session.post(
                f"{self.base_url}/graph",
                timeout_seconds=15,
                data=payload,
            )
            if response.status_code != 200:
                self.log.error(f"bad response status code: {response.status_code}")
                return jobs, None
            res_json = response.json()[0]
            if "errors" in res_json:
                raise ValueError("Error encountered in API response")
        except Exception as e:
            self.log.error(e)
            return jobs, None

        jobs_data = res_json["data"]["jobListings"]["jobListings"]

        with ThreadPoolExecutor(max_workers=self.jobs_per_page) as executor:
            future_to_job_data = {
                executor.submit(self.process_job, job): job for job in jobs_data
            }
            for future in as_completed(future_to_job_data):
                job = future.result()
                if job:
                    jobs.append(job)

        return jobs, self.get_cursor_for_page(res_json["data"]["jobListings"]["paginationCursors"], page_num + 1)

    def _get_csrf_token(self):
        """
        Fetches csrf token needed for API by visiting a generic page
        """
        res = self.session.get(f"{self.base_url}/Job/computer-science-jobs.htm")
        pattern = r'"token":\s*"([^"]+)"'
        matches = re.findall(pattern, res.text)
        token = None
        if matches:
            token = matches[0]
        return token


    def process_job(self, job_data: dict) -> Job | JobReference | None:
        """
        Processes a single job and fetches its description.
        """
        job_id = self.get_id(job_data)
        if f"gd-{job_id}" in self.seen_jobs:
            return JobReference(job_id)

        job_url = self.get_source_url(job_id)
        job_view = job_data["jobview"]
        remote_type = self.get_remote_type(job_view)
        title = self.get_title(job_view)
        job = Job(
            id=f"gd-{job_id}",
            source=Glassdoor.__name__,
            title=title,
            description=self.get_description(job_id),
            company=self.get_company(job_view),
            city=self.city,
            address=self.get_address(job_view, remote_type),
            posted_date=self.get_posted_date(job_view),
            salary=self.get_salary(job_view),
            skills=self.get_skills(),
            experience=self.get_experience(title),
            remote_type=self.get_remote_type(job_view),
            contract_type=self.get_contract_type(),
            source_url=job_url,
            real_url=self.get_real_url(),
            company_url=self.get_company_url(job_view),
            company_logo=self.get_company_logo(job_view),
        )
        self.seen_jobs.add(job_id)
        return job

    def _format_location(self, location: str) -> tuple[int | None, str | None]:
        try:
            url = f"{self.base_url}/findPopularLocationAjax.htm?maxLocationsToReturn=10&term={location}"
            res = self.session.get(url)
            if res.status_code != 200:
                if res.status_code == 429:
                    err = f"429 Response - Blocked by Glassdoor for too many requests"
                    self.log.error(err)
                    return None, None
                if res.status.code == 403:
                    err = "403 Response - Blocked by Glassdoor for being a robot"
                    self.log.error(err)
                    return None, None
                else:
                    err = f"Glassdoor response status code {res.status_code}"
                    self.log.error(err)
                    return None, None
        except Exception as e:
            self.log.error(f"Failed to fetch location for job {location}: {e}")
            return None, None

        items = res.json()
        if not items:
            self.log.error(f"Location '{location}' not found on Glassdoor")
            return None, None

        location_type = items[0]["locationType"]
        if location_type == "C":
            location_type = "CITY"
        elif location_type == "S":
            location_type = "STATE"
        elif location_type == "N":
            location_type = "COUNTRY"
        else:
            self.log.error(f"Location type '{location_type}' not supported")
            location_type = None
        return int(items[0]["locationId"]), location_type

    @staticmethod
    def get_cursor_for_page(pagination_cursors, page_num):
        for cursor_data in pagination_cursors:
            if cursor_data["pageNumber"] == page_num:
                return cursor_data["cursor"]
        return None

    def _add_payload(
        self,
        location_id: int,
        location_type: str,
        page_num: int,
        cursor: str | None = None,
    ) -> str:
        payload = {
            "operationName": "JobSearchResultsQuery",
            "variables": {
                "excludeJobListingIds": [],
                "filterParams": [],
                "keyword": self.scraper_input.search_term,
                "numJobsToShow": 30,
                "locationType": location_type,
                "locationId": int(location_id),
                "parameterUrlInput": f"IL.0,12_I{location_type}{location_id}",
                "pageNumber": page_num,
                "pageCursor": cursor,
                "sort": "date",
            },
            "query": """
                query JobSearchResultsQuery(
                    $excludeJobListingIds: [Long!], 
                    $keyword: String, 
                    $locationId: Int, 
                    $locationType: LocationTypeEnum, 
                    $numJobsToShow: Int!, 
                    $pageCursor: String, 
                    $pageNumber: Int, 
                    $filterParams: [FilterParams], 
                    $originalPageUrl: String, 
                    $seoFriendlyUrlInput: String, 
                    $parameterUrlInput: String, 
                    $seoUrl: Boolean
                ) {
                    jobListings(
                        contextHolder: {
                            searchParams: {
                                excludeJobListingIds: $excludeJobListingIds, 
                                keyword: $keyword, 
                                locationId: $locationId, 
                                locationType: $locationType, 
                                numPerPage: $numJobsToShow, 
                                pageCursor: $pageCursor, 
                                pageNumber: $pageNumber, 
                                filterParams: $filterParams, 
                                originalPageUrl: $originalPageUrl, 
                                seoFriendlyUrlInput: $seoFriendlyUrlInput, 
                                parameterUrlInput: $parameterUrlInput, 
                                seoUrl: $seoUrl, 
                                searchType: SR
                            }
                        }
                    ) {
                        companyFilterOptions {
                            id
                            shortName
                            __typename
                        }
                        filterOptions
                        indeedCtk
                        jobListings {
                            ...JobView
                            __typename
                        }
                        jobListingSeoLinks {
                            linkItems {
                                position
                                url
                                __typename
                            }
                            __typename
                        }
                        jobSearchTrackingKey
                        jobsPageSeoData {
                            pageMetaDescription
                            pageTitle
                            __typename
                        }
                        paginationCursors {
                            cursor
                            pageNumber
                            __typename
                        }
                        indexablePageForSeo
                        searchResultsMetadata {
                            searchCriteria {
                                implicitLocation {
                                    id
                                    localizedDisplayName
                                    type
                                    __typename
                                }
                                keyword
                                location {
                                    id
                                    shortName
                                    localizedShortName
                                    localizedDisplayName
                                    type
                                    __typename
                                }
                                __typename
                            }
                            helpCenterDomain
                            helpCenterLocale
                            jobSerpJobOutlook {
                                occupation
                                paragraph
                                __typename
                            }
                            showMachineReadableJobs
                            __typename
                        }
                        totalJobsCount
                        __typename
                    }
                }
        
                fragment JobView on JobListingSearchResult {
                    jobview {
                        header {
                            adOrderId
                            advertiserType
                            adOrderSponsorshipLevel
                            ageInDays
                            divisionEmployerName
                            easyApply
                            employer {
                                id
                                name
                                shortName
                                __typename
                            }
                            employerNameFromSearch
                            goc
                            gocConfidence
                            gocId
                            jobCountryId
                            jobLink
                            jobResultTrackingKey
                            jobTitleText
                            locationName
                            locationType
                            locId
                            needsCommission
                            payCurrency
                            payPeriod
                            payPeriodAdjustedPay {
                                p10
                                p50
                                p90
                                __typename
                            }
                            rating
                            salarySource
                            savedJobId
                            sponsored
                            __typename
                        }
                        job {
                            description
                            importConfigId
                            jobTitleId
                            jobTitleText
                            listingId
                            __typename
                        }
                        jobListingAdminDetails {
                            cpcVal
                            importConfigId
                            jobListingId
                            jobSourceId
                            userEligibleForAdminJobDetails
                            __typename
                        }
                        overview {
                            shortName
                            squareLogoUrl
                            __typename
                        }
                        __typename
                    }
                    __typename
                }
        """,
        }
        return json.dumps([payload])
