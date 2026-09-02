from datetime import datetime
from pathlib import Path

from config import FILTER_INPUT, SCRAPER_INPUT, SCRAPER_CONFIG, INTEREST_INPUT
from repositories import JobRepository, StatRepository, CompanyRepository
from models.job_response import JobList
from utils.mailer import send_mail
from utils.scrap_all import scrape_jobs


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent
    job_repo = JobRepository()
    company_repo = CompanyRepository()
    stat_repo = StatRepository()
    seen_jobs = job_repo.get_ids()

    jobs = scrape_jobs(SCRAPER_INPUT, SCRAPER_CONFIG, seen_jobs)
    job_list = job_repo.to_job_list(jobs).remove_duplicates().get_company_infos_into_jobs(company_repo)
    filtered = job_list.filter_jobs(FILTER_INPUT).sort_by_interest(INTEREST_INPUT)
    # filtered.to_csv(project_root / "data" / "jobs.csv")
    filtered.create_map(project_root / "web" / "templates" / "jobs_map.html")

    for city in SCRAPER_INPUT.cities:
        job_list_city = JobList([job for job in job_list if job.city == city])
        filtered = JobList([job for job in filtered if job.city == city])
        interest = ((len(filtered) / len(job_list_city)) * 100) if len(job_list_city) > 0 else 0
        today = datetime.today()
        stat_repo.insert_stat(city, today, interest, filtered)

    growth = stat_repo.get_growth()
    new_jobs = job_repo.get_new_jobs(job_list)
    deleted_jobs = job_repo.get_deleted_jobs(job_list)
    already_saved_jobs = job_repo.get_already_saved_jobs(job_list)
    job_repo.update_jobs(new_jobs, deleted_jobs) # job_list)

    new_jobs = new_jobs.filter_jobs(FILTER_INPUT).sort_by_interest(INTEREST_INPUT)
    deleted_jobs = deleted_jobs.filter_jobs(FILTER_INPUT).sort_by_interest(INTEREST_INPUT)
    already_saved_jobs = already_saved_jobs.filter_jobs(FILTER_INPUT).remove_seen_jobs().sort_by_interest(INTEREST_INPUT)
    send_mail(new_jobs, already_saved_jobs, deleted_jobs, growth)
