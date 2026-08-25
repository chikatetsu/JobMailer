# from inputs.filter_input import FilterInput
# from inputs.interest_input import InterestInput
# from inputs.scraper_config import ScraperConfig
# from inputs.scraper_input import ScraperInput
# from models.contract_type import ContractType
# from models.experience import Experience
# from models.site import Site
# from models.remote_type import RemoteType
# from utils.logger import LoggerLevel
#
#
# FRANCE_TRAVAIL_CLIENT_ID = ""
# FRANCE_TRAVAIL_API_KEY = ""
#
# SMTP_SERVER = ""
# SENDER_EMAIL = ""
# SENDER_PASSWORD = ""
#
# FIREFOX_PATH = "/snap/firefox/current/usr/lib/firefox/firefox"
# JOB_MAILER_URL = ""
# JOB_MAILER_PORT = 5000
#
# SCRAPER_INPUT = ScraperInput(
#     search_term="développeur",
#     city="Lyon",
#     distance=20,
# )
#
# SCRAPER_CONFIG = ScraperConfig(
#     websites=[
#         Site.HELLOWORK,
#         Site.TEKKIT,
#         Site.WELCOME_TO_THE_JUNGLE,
#         Site.LINKEDIN,
#         Site.FRANCE_TRAVAIL,
#         Site.INDEED,
#         Site.ZIP_RECRUITER,
#         Site.GOOGLE,
#         Site.GLASSDOOR
#     ],
#     verbose=LoggerLevel.VERBOSE
# )
#
# FILTER_INPUT = FilterInput(
#     remote_types=[RemoteType.ON_SITE, RemoteType.HYBRID, RemoteType.REMOTE],
#     experiences=[
#         Experience.JUNIOR,
#         Experience.MID_LEVEL,
#         Experience.EXPERIENCED,
#         Experience.SENIOR
#     ],
#     contract_types=[
#         ContractType.CDI,
#         ContractType.CDD,
#         ContractType.INTERIM,
#         ContractType.SEASON,
#         ContractType.OTHER,
#         ContractType.INTERNSHIP
#     ],
#     ignore_words=["angular", "cobol", "powershell", "php", "symphony", "mainframe"],
#     ignore_words_in_title=["frontend", "windev", "analyste"]
# )
#
# INTEREST_INPUT = InterestInput(
#     words_in_title={"fullstack": -1, "devops": -2},
#     words_in_description={
#         "python": 10,
#         "rust": 10,
#         "flutter": 2,
#         "c#": 3,
#         "c++": 1,
#         "java": 2,
#         "typescript": 4,
#         "javascript": 1,
#         "kotlin": 3,
#         "nodejs": 1,
#         "nest": 4,
#         "vuejs": 4,
#         "cobol": -10,
#         "powershell": -10,
#         "symphony": -10,
#         "mainframe": -10,
#         "php": -10,
#         "angular": -10,
#         "cleancode": 2,
#         "api": 1,
#     },
# )
#