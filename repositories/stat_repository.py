import sqlite3
from datetime import datetime
from pathlib import Path

from dateutil.relativedelta import relativedelta

from models.city import City
from models.job_response import JobList
from scrapers.francetravail import FranceTravail
from scrapers.glassdoor import Glassdoor
from scrapers.google_search import GoogleSearch
from scrapers.hellowork import HelloWork
from scrapers.indeed import Indeed
from scrapers.linkedin import LinkedIn
from scrapers.tekkit import Tekkit
from scrapers.welcometothejungle import WelcomeToTheJungle
from scrapers.ziprecruiter import ZipRecruiter


class StatRepository:
    def __init__(self):
        project_root = Path(__file__).resolve().parent.parent
        bdd_name = project_root / "data" / "db" / "jobs.db"
        self.conn = sqlite3.connect(bdd_name)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insert_date DATE,
                city TEXT NOT NULL,
                interest FLOAT,
                nb_jobs INTEGER,
                hellowork_source_count INTEGER DEFAULT 0,
                tekkit_source_count INTEGER DEFAULT 0,
                welcome_to_the_jungle_source_count INTEGER DEFAULT 0,
                linkedin_source_count INTEGER DEFAULT 0,
                france_travail_source_count INTEGER DEFAULT 0,
                indeed_source_count INTEGER DEFAULT 0,
                zip_recruiter_source_count INTEGER DEFAULT 0,
                google_source_count INTEGER DEFAULT 0,
                glassdoor_source_count INTEGER DEFAULT 0
            )
        """)
        self.conn.row_factory = sqlite3.Row

    def insert_stat(self, city: City, insert_date: datetime, interest: float, interesting_jobs: JobList):
        source_counts = {}
        for job in interesting_jobs:
            if job.source not in source_counts:
                source_counts[job.source] = 1
            else:
                source_counts[job.source] += 1

        self.conn.execute("""
            INSERT INTO statistics (
                insert_date, city, interest, nb_jobs, hellowork_source_count, tekkit_source_count,
                welcome_to_the_jungle_source_count, linkedin_source_count, france_travail_source_count,
                indeed_source_count, zip_recruiter_source_count, google_source_count, glassdoor_source_count
            ) VALUES (
                :insert_date, :city, :interest, :nb_jobs, :hellowork_source_count, :tekkit_source_count,
                :welcome_to_the_jungle_source_count, :linkedin_source_count, :france_travail_source_count,
                :indeed_source_count, :zip_recruiter_source_count, :google_source_count, :glassdoor_source_count
            )
        """, {
            'insert_date': insert_date,
            'city': city.value.name,
            'interest': interest,
            'nb_jobs': len(interesting_jobs),
            'hellowork_source_count': source_counts.get(HelloWork.__name__, 0),
            'tekkit_source_count': source_counts.get(Tekkit.__name__, 0),
            'welcome_to_the_jungle_source_count': source_counts.get(WelcomeToTheJungle.__name__, 0),
            'linkedin_source_count': source_counts.get(LinkedIn.__name__, 0),
            'france_travail_source_count': source_counts.get(FranceTravail.__name__, 0),
            'indeed_source_count': source_counts.get(Indeed.__name__, 0),
            'zip_recruiter_source_count': source_counts.get(ZipRecruiter.__name__, 0),
            'google_source_count': source_counts.get(GoogleSearch.__name__, 0),
            'glassdoor_source_count': source_counts.get(Glassdoor.__name__, 0),
        })
        self.conn.commit()

    def get_growth(self):
        latest = self.conn.execute("SELECT insert_date, nb_jobs FROM statistics ORDER BY insert_date DESC LIMIT 1").fetchone()
        if latest is None:
            return 0

        latest_nb_jobs = latest["nb_jobs"]
        latest_date = datetime.fromisoformat(latest["insert_date"])
        target_date = latest_date - relativedelta(months=1)

        previous = self.conn.execute(
            "SELECT nb_jobs FROM statistics WHERE insert_date != ? ORDER BY ABS(julianday(insert_date) - julianday(?)), insert_date DESC LIMIT 1", (
            latest["insert_date"],
            target_date.isoformat(),
        )).fetchone()
        if previous is None:
            return 0

        previous_nb_jobs = previous["nb_jobs"]
        growth = round(((latest_nb_jobs - previous_nb_jobs) / previous_nb_jobs) * 100, 2)
        return growth
