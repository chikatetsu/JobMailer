from utils.logger import LoggerLevel
from models.site import Site


class ScraperConfig:
    def __init__(self,
                 websites: list[Site] | None = None,
                 proxies: list[str] | str | None = None,
                 ca_cert: str | None = None,
                 verbose: LoggerLevel = LoggerLevel.ONLY_ERRORS
        ):
        self.websites = self._init_websites(websites)
        self.proxies = proxies
        self.ca_cert = ca_cert
        self.verbose = verbose

    @staticmethod
    def _init_websites(websites: list[Site] | None) -> list[Site]:
        if websites is None:
            websites = list(Site)
        return websites
