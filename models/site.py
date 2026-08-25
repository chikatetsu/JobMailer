from enum import Enum


class Site(Enum):
    LINKEDIN = "LinkedIn"
    INDEED = "Indeed"
    ZIP_RECRUITER = "ZipRecruiter"
    GLASSDOOR = "Glassdoor"
    GOOGLE = "GoogleSearch"
    BAYT = "BaytScraper"
    FRANCE_TRAVAIL = "FranceTravail"
    HELLOWORK = "HelloWork"
    TEKKIT = "Tekkit"
    WELCOME_TO_THE_JUNGLE = "WelcomeToTheJungle"

    def __str__(self):
        return self.value
