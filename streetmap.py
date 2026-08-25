import time

import folium
from folium.plugins import Geocoder
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

from config import SCRAPER_INPUT
from repositories import CompanyRepository
from utils.company_sorting import DevHiring


class Point:
    def __init__(self, names, address, radius, priority):
        self.names = names
        self.address = address
        self.radius = radius
        self.priority = priority

    def priority_to_color(self, max_val=130):
        # t = max(0, min(1, self.priority / max_val))  # 0.0 → 1.0
        # if t < 0.5:
        #     r = int(min(255 * t * 2, 255))
        #     g = 224
        # else:
        #     r = 255
        #     g = int(min(224 * (1 - ((t - 0.5) * 2)), 224))
        # return f"#{r:02x}{g:02x}00"
        if self.priority == DevHiring.YES.value:
            return "red"
        elif self.priority == DevHiring.PROBABLY.value:
            return "yellow"
        elif self.priority == DevHiring.DOUBT.value:
            return "green"
        else:
            return "gray"


if __name__ == "__main__":
    repo = CompanyRepository()
    companies = repo.get_all_companies(SCRAPER_INPUT.cities)

    geolocator = Nominatim(user_agent="mon_app_carte")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    # Géocoder toutes les adresses
    points = {}
    for company in companies:
        if company.dev_hiring in {DevHiring.DOUBT, DevHiring.NO, DevHiring.UNKNOWN}:
            continue
        company_location = company.address
        if company.lat is None or company.lon is None:
            time.sleep(1)
            location = geocode(company_location)
            if not location:
                print(f"✗ NOT FOUND\t{company.name}\t\t{company_location}")
                continue

            company.lat = location.latitude
            company.lon = location.longitude
            repo.update_company(company.id, company)
            repo.commit()
            print(f"✓ \t\t\t{company.name}\t\t{company_location}")
        if points.get((company.lat, company.lon), None) is None:
            points[company.lat, company.lon] = Point(
                names=f"<a href=\"{company.url}\">- {company.name.title()}</a>",
                address=company.address,
                radius=1,
                priority=company.dev_hiring.value
            )
        else:
            points[(company.lat, company.lon)].names += f"</br><a href=\"{company.url}\">- {company.name.title()}</a>"
            points[(company.lat, company.lon)].radius += 1
            points[(company.lat, company.lon)].priority = max(points[(company.lat, company.lon)].priority, company.dev_hiring.value)

    # Créer la carte centrée sur la ville
    if points:
        city_location = geocode(f"{SCRAPER_INPUT.cities[0]} France")
        carte = folium.Map(location=[city_location.latitude, city_location.longitude], zoom_start=13)

        sorted_points = sorted([(lat, lon, point) for (lat, lon), point in points.items()], key=lambda p: p[2].priority)
        for (lat, lon, point) in sorted_points:
            folium.CircleMarker(
                location=[lat, lon],
                radius=point.radius * 2,
                color=point.priority_to_color(53),
                fill=True,
                fill_opacity=0.8,
                opacity=0.0,
                popup=point.names,
                tooltip=point.address,
            ).add_to(carte)

        Geocoder().add_to(carte)

        # Sauvegarder en HTML
        carte.save("web/templates/companies_map.html")
        print("\nCarte sauvegardée")
