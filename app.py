from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, redirect, jsonify, abort, request

from config import INTEREST_INPUT, FILTER_INPUT, SCRAPER_INPUT, JOB_MAILER_PORT
from models.candidate_status import CandidateStatus
from models.city import City
from models.contract_type import ContractType
from models.experience import Experience
from models.site import Site
from models.remote_type import RemoteType
from utils.logger import LoggerLevel
from repositories import JobRepository, CompanyRepository


project_root = Path(__file__).resolve().parent
template_folder = project_root / "web" / "templates"
static_folder = project_root / "web" / "static"

app = Flask(
    __name__,
    template_folder=template_folder,
    static_folder=static_folder,
)
job_repo = JobRepository(check_same_thread=False)
company_repo = CompanyRepository(check_same_thread=False)


### UTILS ###

def _enum_label(member):
    """Libellé lisible pour un membre d'enum, même quand .value est un objet"""
    val = member.value
    if hasattr(val, "name"):
        return val.name.replace("_", " ").title()
    return str(val)

def _enum_options(enum_cls):
    return [{"name": m.name, "label": _enum_label(m)} for m in enum_cls]

def _dict_to_pairs(d):
    return [{"mot": k, "score": v} for k, v in (d or {}).items()]

def _parse_word_list(raw):
    return [w.strip() for w in raw.split(",") if w.strip()]

def _parse_words_dict(form, prefix):
    """Reconstruit {mot: score} depuis des champs {prefix}_mot_0/{prefix}_score_0, ..."""
    result = {}
    i = 0
    while f"{prefix}_mot_{i}" in form:
        mot = form.get(f"{prefix}_mot_{i}", "").strip()
        score = form.get(f"{prefix}_score_{i}", "").strip()
        if mot and score:
            try:
                result[mot] = int(score)
            except ValueError:
                pass
        i += 1
    return result

def _build_context(cfg):
    return {
        "france_travail_client_id": cfg.FRANCE_TRAVAIL_CLIENT_ID,
        "france_travail_api_key": cfg.FRANCE_TRAVAIL_API_KEY,
        "smtp_server": cfg.SMTP_SERVER,
        "sender_email": cfg.SENDER_EMAIL,
        "sender_password": cfg.SENDER_PASSWORD,
        "firefox_path": cfg.FIREFOX_PATH,
        "search_term": cfg.SCRAPER_INPUT.search_term,
        "cities": cfg.SCRAPER_INPUT.cities,
        "distance": cfg.SCRAPER_INPUT.distance,
        "verbose": cfg.SCRAPER_CONFIG.verbose.name,
        "websites_selected": {s.name for s in cfg.SCRAPER_CONFIG.websites},
        "remote_types_selected": {r.name for r in cfg.FILTER_INPUT.remote_types},
        "experiences_selected": {e.name for e in cfg.FILTER_INPUT.experiences},
        "contract_types_selected": {c.name for c in cfg.FILTER_INPUT.contract_types},
        "ignore_words": ", ".join(cfg.FILTER_INPUT.ignore_words),
        "ignore_words_in_title": ", ".join(cfg.FILTER_INPUT.ignore_words_in_title),
        "words_in_title": _dict_to_pairs(cfg.INTEREST_INPUT.words_in_title),
        "words_in_description": _dict_to_pairs(cfg.INTEREST_INPUT.words_in_description),
    }

def _build_options():
    return {
        "cities": _enum_options(City),
        "sites": _enum_options(Site),
        "logger_levels": _enum_options(LoggerLevel),
        "remote_types": _enum_options(RemoteType),
        "experiences": _enum_options(Experience),
        "contract_types": _enum_options(ContractType),
    }


### WEB PAGES ###

@app.route("/")
def index():
    jobs = job_repo.get_all_jobs()
    sorted_jobs = jobs.filter_jobs(FILTER_INPUT).sort_by_interest(INTEREST_INPUT)
    return render_template("index.html", jobs=sorted_jobs.jobs, active_page="jobs")

@app.route("/companies")
def companies():
    companies_list = company_repo.get_all_companies(SCRAPER_INPUT.cities)
    scored_companies = { company.id : [company, 0] for company in companies_list }
    jobs = job_repo.get_all_jobs()
    for job in jobs:
        if job.company_id is not None:
            scored_companies[job.company_id][1] += 1
    sorted_companies = [company[0] for company in sorted(scored_companies.values(), key=lambda c: c[1], reverse=True)]
    return render_template("companies.html", companies=sorted_companies, active_page="companies")

@app.route("/jobs-map")
def jobs_map():
    return render_template("jobs_map_page.html", active_page="jobs-map")

@app.route("/companies-map")
def companies_map():
    return render_template("companies_map_page.html", active_page="companies-map")

@app.route("/raw/jobs-map")
def raw_job_map():
    return render_template("jobs_map.html")

@app.route("/raw/companies-map")
def raw_company_map():
    return render_template("companies_map.html")

@app.route("/job_map")
def job_map():
    return render_template("job_map.html")


### API ###

@app.route("/redirect/<job_id>")
def see_job(job_id):
    success = job_repo.see_job(job_id)
    if not success:
        abort(404)

    job = job_repo.get_job_by_id(job_id)
    if job is None:
        abort(404)
    if job.real_url != "":
        return redirect(job.real_url, code=302)
    return redirect(job.source_url, code=302)

@app.route("/api/mark_as_seen/<job_id>", methods=["POST"])
def mark_as_seen(job_id):
    success = job_repo.see_job(job_id)
    if not success:
        abort(404)
    return jsonify({"ok": True})

@app.route("/api/mark_as_unseen/<job_id>", methods=["POST"])
def mark_as_unseen(job_id):
    success = job_repo.unsee_job(job_id)
    if not success:
        abort(404)
    return jsonify({"ok": True})

@app.route("/api/update_candidate_status/<job_id>", methods=["POST"])
def update_candidate_status(job_id):
    candidate_status_raw = request.args.get('candidate_status', None)
    if candidate_status_raw is None:
        abort(400)
    candidate_status = CandidateStatus.from_str(candidate_status_raw)
    if candidate_status is None:
        abort(400)
    candidate_date = request.args.get('candidate_date', None)
    if candidate_date is not None:
        candidate_date = datetime.strptime(candidate_date, "%Y-%m-%d %H:%M:%S")
    success = job_repo.update_candidate_status(job_id, candidate_status, candidate_date)
    if not success:
        abort(404)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=JOB_MAILER_PORT, debug=False)
