import sqlite3
from datetime import datetime
from pathlib import Path

from models.candidate_status import CandidateStatus
from models.city import City
from models.contract_type import ContractType
from models.experience import Experience
from models.job import Job, JobReference
from models.job_response import JobResponse, JobList
from models.remote_type import RemoteType
from models.salary import Salary
from utils.logger import create_logger


class JobRepository:
    def __init__(self, check_same_thread: bool = True):
        project_root = Path(__file__).resolve().parent.parent
        bdd_name = project_root / "data" / "db" / "jobs.db"
        self.conn = sqlite3.connect(bdd_name, check_same_thread=check_same_thread)
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                source TEXT,
                title TEXT,
                description TEXT,
                city TEXT,
                company TEXT,
                address TEXT,
                lat REAL,
                lon REAL,
                posted_date DATE,
                salary_min INTEGER DEFAULT 0,
                salary_max INTEGER DEFAULT 0,
                skills TEXT,
                experience TEXT,
                remote_type TEXT,
                contract_type TEXT,
                source_url TEXT,
                real_url TEXT,
                company_url TEXT,
                company_logo TEXT,
                company_id INTEGER,
                interest INTEGER DEFAULT 0,
                is_seen BOOLEAN DEFAULT FALSE,
                is_ignored BOOLEAN DEFAULT FALSE,
                candidate_status TEXT DEFAULT '{str(CandidateStatus.NOT_APPLIED)}',
                candidate_date DATE
            )
        """)
        self.conn.row_factory = sqlite3.Row
        self.log = create_logger(JobRepository.__name__)

    def get_all_jobs(self) -> JobList:
        jobs = []
        cursor = self.conn.execute("SELECT * FROM jobs")
        for row in cursor:
            try:
                job = self._row_to_job(row)
                jobs.append(job)
            except Exception as e:
                self.log.error(f"Couldn't get job from database with id {row['id']} : {e}")
        return JobList(jobs)

    def get_new_jobs(self, jobs: JobList) -> JobList:
        new_jobs = []
        for job in jobs:
            cursor = self.conn.execute("SELECT 1 FROM jobs WHERE id = ?", (job.id,))
            if not cursor.fetchone():
                new_jobs.append(job)
        return JobList(new_jobs)

    def get_deleted_jobs(self, jobs: JobList) -> JobList:
        deleted_jobs = []
        job_ids = {job.id for job in jobs}
        cursor = self.conn.execute("SELECT * FROM jobs")
        for row in cursor:
            if row["id"] not in job_ids:
                try:
                    job = self._row_to_job(row)
                    deleted_jobs.append(job)
                except Exception as e:
                    self.log.error(f"Couldn't get job from database with id {row['id']} : {e}")
        return JobList(deleted_jobs)

    def get_already_saved_jobs(self, jobs: JobList) -> JobList:
        saved_jobs = []
        job_map = {job.id: job for job in jobs}
        cursor = self.conn.execute("SELECT * FROM jobs")
        for row in cursor:
            if row["id"] in job_map.keys():
                job = job_map[row["id"]]
                saved_jobs.append(job)
        return JobList(saved_jobs)

    @staticmethod
    def _row_to_job(row: dict) -> Job:
        job = Job(
            id=row["id"],
            source=row["source"],
            title=row["title"],
            description=row["description"],
            company=row["company"],
            city=City.from_str(row["city"]),
            address=row["address"] if row["address"] else "",
            lat=row["lat"],
            lon=row["lon"],
            posted_date=row["posted_date"],
            salary=Salary(min_amount=row["salary_min"], max_amount=row["salary_max"]),
            skills=row["skills"].split(", "),
            experience=Experience.from_str(row["experience"]),
            remote_type=RemoteType.from_str(row["remote_type"]),
            contract_type=ContractType.from_str(row["contract_type"]),
            source_url=row["source_url"],
            real_url=row["real_url"],
            company_url=row["company_url"],
            company_logo=row["company_logo"],
            company_id=row["company_id"],
            interest=row["interest"],
            is_seen=row["is_seen"],
            is_ignored=row["is_ignored"],
            candidate_status=CandidateStatus.from_str(row["candidate_status"]),
            candidate_date=row["candidate_date"],
        )
        return job

    def get_job_by_id(self, job_id: str) -> Job | None:
        cursor = self.conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        for row in cursor:
            job = self._row_to_job(row)
            return job
        return None

    def get_ids(self) -> set[str]:
        ids = set()
        cursor = self.conn.execute("SELECT id FROM jobs")
        for row in cursor:
            ids.add(row["id"])
        return ids

    def to_job_list(self, job_response: JobResponse) -> JobList:
        job_list = []
        for job in job_response:
            if isinstance(job, Job):
                job_list.append(job)
            elif isinstance(job, JobReference):
                full_job = self.get_job_by_id(job.id)
                job_list.append(full_job)
        return JobList(job_list)

    def update_jobs(self, new_jobs: JobList, deleted_jobs: JobList):
        try:
            for job in deleted_jobs:
                self.conn.execute("DELETE FROM jobs WHERE id = ? AND candidate_status  IN ('Not applied', 'Rejected')", (job.id,))

            for job in new_jobs:
                self.conn.execute("""
                    INSERT INTO jobs (
                        id, source, title, description, company, city, address, lat, lon, posted_date, salary_min, salary_max,
                        skills, experience, remote_type, contract_type, source_url, real_url, company_url, company_logo,
                        company_id, interest, is_seen, is_ignored, candidate_status, candidate_date
                    ) VALUES (
                         :id, :source, :title, :description, :company, :city, :address, :lat, :lon, :posted_date, :salary_min, :salary_max,
                         :skills, :experience, :remote_type, :contract_type, :source_url, :real_url, :company_url, :company_logo,
                         :company_id, :interest, :is_seen, :is_ignored, :candidate_status, :candidate_date
                    )""", {
                    "id": job.id,
                    "source": job.source,
                    "title": job.title,
                    "description": job.description,
                    "company": job.company,
                    "city": str(job.city),
                    "address": job.address,
                    "lat": job.lat,
                    "lon": job.lon,
                    "posted_date": datetime.now(),
                    "salary_min": job.salary.min_amount if job.salary else 0,
                    "salary_max": job.salary.max_amount if job.salary else 0,
                    "skills": ", ".join(job.skills),
                    "experience": str(job.experience),
                    "remote_type": str(job.remote_type),
                    "contract_type": str(job.contract_type),
                    "source_url": job.source_url,
                    "real_url": job.real_url,
                    "company_url": job.company_url,
                    "company_logo": job.company_logo,
                    "company_id": job.company_id,
                    "interest": job.interest,
                    "is_seen": job.is_seen,
                    "is_ignored": job.is_ignored,
                    "candidate_status": str(job.candidate_status),
                    "candidate_date": job.candidate_date
                })
            self.conn.commit()
        except Exception as e:
            self.log.error(f"Couldn't insert new jobs : {e}")
    # def update_jobs(self, jobs: JobList):
    #     try:
    #         self.conn.execute("DELETE FROM jobs")
    #         for job in jobs:
    #             self.conn.execute("""
    #                 INSERT INTO jobs (
    #                     id, source, title, description, company, city, address, lat, lon, posted_date, salary_min,
    #                     salary_max, skills, experience, remote_type, contract_type, source_url, real_url, company_url,
    #                     company_logo, company_id, interest, is_seen, is_ignored, candidate_status, candidate_date
    #                 ) VALUES (
    #                      :id, :source, :title, :description, :company, :city, :address, :lat, :lon, :posted_date, :salary_min,
    #                      :salary_max, :skills, :experience, :remote_type, :contract_type, :source_url, :real_url, :company_url,
    #                      :company_logo, :company_id, :interest, :is_seen, :is_ignored, :candidate_status, :candidate_date
    #                 )""", {
    #                 "id": job.id,
    #                 "source": job.source,
    #                 "title": job.title,
    #                 "description": job.description,
    #                 "company": job.company,
    #                 "city": str(job.city),
    #                 "address": job.address,
    #                 "lat": job.lat,
    #                 "lon": job.lon,
    #                 "posted_date": job.posted_date,
    #                 "salary_min": job.salary.min_amount if job.salary else 0,
    #                 "salary_max": job.salary.max_amount if job.salary else 0,
    #                 "skills": ", ".join(job.skills),
    #                 "experience": str(job.experience),
    #                 "remote_type": str(job.remote_type),
    #                 "contract_type": str(job.contract_type),
    #                 "source_url": job.source_url,
    #                 "real_url": job.real_url,
    #                 "company_url": job.company_url,
    #                 "company_logo": job.company_logo,
    #                 "company_id": job.company_id,
    #                 "interest": job.interest,
    #                 "is_seen": job.is_seen,
    #                 "is_ignored": job.is_ignored,
    #                 "candidate_status": str(job.candidate_status),
    #                 "candidate_date": job.candidate_date,
    #             })
    #         self.conn.commit()
    #     except Exception as e:
    #         self.log.error(f"Couldn't insert new jobs : {e}")

    def see_job(self, job_id: str) -> bool:
        try:
            self.conn.execute("""UPDATE jobs SET is_seen = :is_seen WHERE id = :id""", {
                "is_seen": True,
                "id": job_id,
            })
            self.conn.commit()
            return True
        except Exception as e:
            self.log.error(f"Couldn't see_job() : {e}")
            return False

    def unsee_job(self, job_id: str) -> bool:
        try:
            self.conn.execute("""UPDATE jobs SET is_seen = :is_seen WHERE id = :id""", {
                "is_seen": False,
                "id": job_id,
            })
            self.conn.commit()
            return True
        except Exception as e:
            self.log.error(f"Couldn't unsee_job() : {e}")
            return False

    def ignore_job(self, job_id: str) -> bool:
        try:
            self.conn.execute("""UPDATE jobs SET is_ignored = :is_ignored WHERE id = :id""", {
                "is_ignored": True,
                "id": job_id,
            })
            self.conn.commit()
            return True
        except Exception as e:
            self.log.error(f"Couldn't ignore_job() : {e}")
            return False

    def unignore_job(self, job_id: str) -> bool:
        try:
            self.conn.execute("""UPDATE jobs SET is_ignored = :is_ignored WHERE id = :id""", {
                "is_ignored": False,
                "id": job_id,
            })
            self.conn.commit()
            return True
        except Exception as e:
            self.log.error(f"Couldn't unignore_job() : {e}")
            return False

    def update_candidate_status(self, job_id: str, candidate_status: CandidateStatus, candidate_date: datetime | None) -> bool:
        if candidate_date is None:
            self.conn.execute("""UPDATE jobs SET candidate_status = :candidate_status WHERE id = :id""", {
                "candidate_status": str(candidate_status),
                "id": job_id,
            })
        else:
           self.conn.execute("""
                UPDATE jobs
                SET candidate_status = :candidate_status, candidate_date = :candidate_date
                WHERE id = :id
                """, {
                "candidate_status": str(candidate_status),
                "candidate_date": candidate_date,
                "id": job_id,
            })
        try:
            self.conn.commit()
            return True
        except Exception as e:
            self.log.error(f"Couldn't update_candidate_status() : {e}")
            return False
