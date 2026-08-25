import csv
import io
import re
from typing import Iterator, Self

import folium

from inputs.filter_input import FilterInput
from inputs.interest_input import InterestInput
from repositories import CompanyRepository
from .job import Job, JobReference


class JobList:
    def __init__(self, jobs: list[Job] | None = None):
        self.jobs = jobs if jobs else []

    def filter_jobs(self, filter_input: FilterInput) -> "JobList":
        filtered_jobs = []
        for job in self.jobs:
            if job.remote_type not in filter_input.remote_types:
                continue
            if job.experience is not None and job.experience not in filter_input.experiences:
                continue
            if job.contract_type not in filter_input.contract_types:
                continue
            all_text = job.title + job.description + "".join(job.skills)
            all_text = all_text.replace(" ", "").replace("\n", "").replace("-", "").strip().lower()
            if any(word in all_text for word in filter_input.ignore_words):
                continue
            formatted_title = job.title.replace(" ", "").replace("\n", "").replace("-", "").strip().lower()
            if any(word in formatted_title for word in filter_input.ignore_words_in_title):
                continue
            filtered_jobs.append(job)
        return JobList(filtered_jobs)

    def remove_duplicates(self) -> "JobList":
        filtered_jobs = []
        visited_id = set()
        visited_source_url = set()
        visited_real_url = set()
        visited_text = set()
        for job in self.jobs:
            if job is None:
                continue
            if job.id in visited_id:
                continue
            if job.source_url != "" and job.source_url in visited_source_url:
                continue
            if job.real_url != "" and job.real_url in visited_real_url:
                continue
            text = job.title + job.company
            text = text.replace(" ", "").replace("\n", "").replace("-", "").strip().lower()
            if text in visited_text:
                continue

            pattern = r"\s*\(?[HF]\s*/\s*[FH]\)?"
            title = re.sub(pattern, "", job.title, flags=re.IGNORECASE).strip()
            if title.endswith("-"):
                title = title[:-1].strip()
            job.title = title

            filtered_jobs.append(job)
            visited_id.add(job.id)
            visited_source_url.add(job.source_url)
            visited_real_url.add(job.real_url)
            visited_text.add(text)
        return JobList(filtered_jobs)

    def remove_seen_jobs(self) -> "JobList":
        filtered_jobs = []
        for job in self.jobs:
            if not job.is_seen:
                filtered_jobs.append(job)
        return JobList(filtered_jobs)

    def sort_by_interest(self, interest_input: InterestInput) -> "JobList":
        for job in self.jobs:
            job.get_interest(interest_input)
        sorted_jobs = sorted(
            self.jobs,
            key=lambda t: t.interest,
            reverse=True
        )
        return JobList(sorted_jobs)

    def get_company_infos_into_jobs(self, company_repo: CompanyRepository) -> "JobList":
        for job in self.jobs:
            job.get_company_infos(company_repo,False)
        company_repo.commit()
        return JobList(self.jobs)

    def to_csv(self, filepath: str | None = None) -> str:
        fieldnames = self.jobs[0].to_dict().keys()
        if fieldnames == [] and filepath is not None:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                f.write("")
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        writer.writerows(job.to_dict() for job in self.jobs)
        content = output.getvalue()
        if filepath:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                f.write(content)
        return content

    def create_map(self, filepath: str):
        points = {}
        for job in self.jobs:
            if job.lat is None or job.lon is None:
                continue
            if points.get((job.lat, job.lon), None) is None:
                points[job.lat, job.lon] = [
                    f"<a href=\"/redirect/{job.id}\">{job.title} - {job.company.title()}</a>",
                    job.address,
                    1
                ]
            else:
                points[(job.lat, job.lon)][0] += f"<a href=\"/redirect/{job.id}\">{job.title} - {job.company.title()}</a>"
                points[(job.lat, job.lon)][2] += 1

        first_point: tuple = next(iter(points))
        carte = folium.Map(location=[first_point[0], first_point[1]], zoom_start=13)
        for (lat, lon), infos in points.items():
            name = infos[0]
            address = infos[1]
            radius = infos[2]
            folium.CircleMarker(
                location=[lat, lon],
                radius=radius * 2,
                color="red",
                fill=True,
                fill_opacity=0.8,
                opacity=0.0,
                popup=name,
                tooltip=address,
            ).add_to(carte)
        carte.save(filepath)

    def to_dict(self) -> list[dict]:
        job_dict: list[dict] = []
        for job in self.jobs:
            job_dict.append(job.to_dict())
        return job_dict

    def __iter__(self) -> Iterator[Job]:
        for job in self.jobs:
            yield job

    def __add__(self, other: Self) -> Self:
        self.jobs.extend(other.jobs)
        return self

    def __len__(self) -> int:
        return len(self.jobs)

    def __getitem__(self, item):
        return self.jobs[item]


class JobResponse:
    def __init__(self, jobs: list[Job | JobReference] | None = None):
        self.jobs = jobs if jobs else []

    def __iter__(self) -> Iterator[Job | JobReference]:
        for job in self.jobs:
            yield job

    def __add__(self, other: Self) -> Self:
        self.jobs.extend(other.jobs)
        return self

    def __len__(self) -> int:
        return len(self.jobs)

    def __getitem__(self, item):
        return self.jobs[item]
