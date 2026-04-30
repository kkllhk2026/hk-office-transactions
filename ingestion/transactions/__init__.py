from .centaline import CentalineScraper
from .midland import MidlandScraper
from .leasinghub import LeasingHubScraper
from .rvd_official import RVDScraper

ALL_TRANSACTION_SCRAPERS = [
    CentalineScraper,
    MidlandScraper,
    LeasingHubScraper,
    RVDScraper,
]
