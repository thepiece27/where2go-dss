"""Single orchestration entry point for API, evaluation and notebooks."""
from .planner import plan_itinerary
from .ranking import RankingContext
from .trips import recommendations, suggest_trips
from .recommendations import recommend_pois


class ItineraryService:
    def __init__(self, pois, manifest, router):
        self.pois = pois
        self.manifest = manifest
        self.router = router
        self.ranking_context = RankingContext(pois)

    def plan(self, request, method="fuzzy"):
        return plan_itinerary(
            self.pois, self.manifest, request, self.router,
            self.ranking_context, method=method,
        )

    def suggest(self, request):
        return suggest_trips(self.pois, self.manifest, request, self.router, self.ranking_context)

    def recommend(self, request):
        return recommendations(self.pois, self.manifest, request, self.router, self.ranking_context)

    def recommend_pois(self, request):
        return recommend_pois(self.pois, self.manifest, request, self.router, self.ranking_context)
