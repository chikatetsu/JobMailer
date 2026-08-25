from models.city import City


class ScraperInput:
    def __init__(self, search_term: str, cities: list[City] | None = None, distance: int = 0):
        self.search_term = search_term
        self.cities = cities if cities else []
        self._distance = distance if distance > 0 else 0

    def distance(self, allowed_distances: list[int] | None = None) -> int:
        if allowed_distances is None:
            return self._distance
        sorted_distances = sorted(allowed_distances, reverse=True)
        for distance in sorted_distances:
            if self._distance >= distance:
                return distance
        return allowed_distances[0]
