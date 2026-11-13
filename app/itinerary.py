"""
Day-by-day itineraries for the Discover Portugal packages
---------------------------------------------------------
Used by notebook 03 (the standard 7-day trips) and by the Streamlit app (any number of days).

The rules (simple, so we can explain them):
  1. ISLANDS: a trip in the Açores or Madeira stays on ONE island
     (by default the island with the most places of the package theme).
  2. BEACH & SUN: no jumping around. We stay in ONE town (the one with the most Blue Flag beaches)
     and every day we go to a different beach (less than 40 km away), starting with the closest ones.
  3. ALL THE OTHER PACKAGES: a road trip. We start in the town with the most places of the theme
     (UNESCO sites and historic villages count 3 times; in the app the tourist can choose another start),
     and each day we go to the best town less than 60 km away (or, if there is none, the closest one).
  4. HIDDEN GEMS: in trips of 5 days or more, if the region has a hidden gem, one day goes there
     (the gem closest to the start, if it's less than 150 km away).
  5. PLACES PER DAY depend on the theme: 1 beach, 2 natural areas, 2 historic villages, 3 viewpoints,
     4 monuments and museums (culture and mix). If the town has fewer, we add places of the theme
     in the towns around it (less than 25 km away) that are not on the route.
  6. More days than towns (e.g. on a small island): extra days in the town with the most places
     still to see, right after its first day.
  7. ORDER: after choosing the towns, we put them in the order with the SHORTEST total distance,
     as a round trip (we start in the best town and come back to it at the end, e.g. to the airport),
     so the trip never goes back and forth.
  8. The tourist can skip towns: the ones they have already visited, and (if they prefer fewer tourists)
     the busiest towns of the region in that month.
  9. WELL-KNOWN TOWNS (culture and mix trips): the normal days only go to towns in the top 60% of the
     region (or island) by overnight stays, and with at least 8% of the points of the best town (rule 3).
     So a quiet suburb with one old monument (e.g. Seixal, next to Lisbon) doesn't take a day of the trip:
     the big towns get more days instead (rule 6), e.g. 2 days in Lisboa. The hidden gem day (rule 4) is not affected, and this rule
     is off when the tourist prefers fewer tourists.
"""

import math
import re

import pandas as pd

from english import english_name

# Which island is each municipality on (Açores and Madeira)
ISLANDS = {
    "Ponta Delgada": "São Miguel", "Lagoa (Açores)": "São Miguel", "Ribeira Grande": "São Miguel",
    "Vila Franca do Campo": "São Miguel", "Povoação": "São Miguel", "Nordeste": "São Miguel",
    "Angra do Heroísmo": "Terceira", "Vila da Praia da Vitória": "Terceira",
    "Velas": "São Jorge", "Calheta (Açores)": "São Jorge",
    "Madalena": "Pico", "São Roque do Pico": "Pico", "Lajes do Pico": "Pico",
    "Horta": "Faial",
    "Santa Cruz das Flores": "Flores", "Lajes das Flores": "Flores",
    "Santa Cruz da Graciosa": "Graciosa",
    "Vila do Porto": "Santa Maria",
    "Corvo": "Corvo",
    "Porto Santo": "Porto Santo",
    # all the other municipalities of Madeira are on the island of Madeira
    "Calheta (Madeira)": "Madeira", "Câmara de Lobos": "Madeira", "Funchal": "Madeira", "Machico": "Madeira",
    "Ponta do Sol": "Madeira", "Porto Moniz": "Madeira", "Ribeira Brava": "Madeira", "Santa Cruz": "Madeira",
    "Santana": "Madeira", "São Vicente": "Madeira",
}

# Which types of place match each package theme
THEME_CATEGORIES = {
    "beach": ["beach"],
    "nature": ["nature"],
    "viewpoint": ["nature", "viewpoint"],
    "countryside": ["countryside"],
    "culture": ["culture"],
    "mix": ["culture", "nature", "beach", "countryside", "viewpoint"],   # the tourist chooses which ones
}

# Order of importance of the places (lower = more important)
IMPORTANCE = {"UNESCO World Heritage": 0, "Aldeias Históricas de Portugal": 1,
              "National Monument": 2, "Aldeias do Xisto": 2}

# Natural areas that come first: parks, protected landscapes, natural monuments and reserves
NATURE_HIGHLIGHTS = "^Parque|Nature Park|Natural Park|Paisagem Protegida|Monumento Natural|Reserva Natural"

MAX_DAY_TRIP_KM = 60     # rule 3: the next town must be less than 60 km away
MAX_GEM_KM = 150         # rule 4: the hidden gem must be less than 150 km from the start
MAX_BEACH_KM = 40        # rule 2: beaches less than 40 km from the base town
NEARBY_KM = 25           # rule 5: places in the towns around, to complete a day
KNOWN_TOWNS = 0.4        # rule 9: skip the 40% of towns with the fewest overnight stays (culture and mix)
MIN_POINTS = 0.08        # rule 9: and the towns with less than 8% of the points of the best town

# Rule 5: how many places fit in one day, for each theme
# (a beach or a big park takes the whole day; in a historic town you see several monuments)
PLACES_PER_DAY = {"beach": 1, "nature": 2, "countryside": 2, "viewpoint": 3, "culture": 4, "mix": 4}


def distance_km(lat1, lon1, lat2, lon2):
    """Distance in a straight line between 2 points on Earth (haversine formula)"""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


# Places that don't interest tourists (even when they are classified): small churches and chapels,
# pillories, crosses, fountains, tombs, houses, road markers... We keep castles, monasteries, cathedrals,
# palaces, historic centres, villages, beaches, parks, viewpoints and the big churches.
NOT_FOR_TOURISTS = ("^(?:Igreja matriz|Igreja paroquial|Igreja e |Capela|Ermida|Pelourinho|Cruzeiro|Chafariz|Túmulo|"
                    "Casa|Edifício|Prédio|Imóvel|Moradia|Solar|Quinta|Marco|Padrão|Alminhas|Fonte|Escola|Conjunto|"
                    "Estátua|Lápide|Inscrição|Sepultura|Estação da|Estação Elevatória|Empreendimento|Açude|Via romana|"
                    "Vias antigas|Troço|Calçada|Portal|Portas|Janela|Cortinas|Palacete|Cerca medieval|Zona Especial|"
                    "IBA |Monte Submarino|Campo Hidrotermal|Pedestrian bridge|Airplane|Parque Empresarial|Miradouro$)")


def tourist_places(places):
    """Only the places a tourist would like to visit:
    - not the types in NOT_FOR_TOURISTS
    - monuments and museums: only with an official quality marker, or a national museum"""
    boring = places["name"].str.contains(NOT_FOR_TOURISTS, case=False, na=False)
    weak_culture = ((places["category"] == "culture") & (places["quality_marker"] != True)
                    & ~places["name"].str.startswith("Museu Nacional", na=False))
    return places[~boring & ~weak_culture]


def theme_categories(package):
    """The types of place of a package (a "mix" package can have its own list, chosen by the tourist)"""
    chosen = package.get("categories", None)
    return chosen if isinstance(chosen, list) and chosen else THEME_CATEGORIES[package["specialty"]]


def mixed_order(town_places):
    """Mix trips: one place of each type in turn (e.g. a monument, then a beach, then a park...),
    so each day mixes different things. town_places is already sorted by importance."""
    by_type = [list(group["name"]) for _, group in town_places.groupby("category", sort=False)]
    order = []
    for i in range(max(len(names) for names in by_type)):
        order += [names[i] for names in by_type if i < len(names)]
    return order


def theme_places(places, package, island=None):
    """The places of the package theme in the region (or island), most important first"""
    places = tourist_places(places)
    chosen = places[(places["region"] == package["region"])
                    & (places["category"].isin(theme_categories(package)))].copy()
    # Places a tourist can't visit: underwater areas in the ocean, and airport runways (OpenStreetMap)
    cannot_visit = chosen["name"].str.contains("Submarino|Hidrotermal|Oceânica|^Banco |^Baixa |runway", na=False)
    chosen = chosen[~cannot_visit]
    if island:
        chosen = chosen[chosen["municipality"].map(ISLANDS) == island]

    chosen["importance"] = chosen["subcategory"].map(IMPORTANCE).fillna(5)
    # Natural areas: parks, protected landscapes, natural monuments and reserves come first
    chosen.loc[chosen["name"].str.contains(NATURE_HIGHLIGHTS, na=False), "importance"] = 1
    return chosen.sort_values(["importance", "quality_marker"], ascending=[True, False])


def start_options(places, package, island=None, visited=()):
    """Towns where the trip can start: all the towns of the theme, best first (the first one is the default)"""
    chosen = theme_places(places, package, island)
    chosen = chosen[~chosen["municipality"].isin(visited)] if (~chosen["municipality"].isin(visited)).any() else chosen
    return list(town_scores(chosen).index)


def best_island(places, package):
    """Rule 1: the island with the most places of the package theme"""
    chosen = theme_places(places, package)
    return chosen["municipality"].map(ISLANDS).value_counts().index[0]


# The most special places count 3 times when we choose the best towns
SPECIAL = ["UNESCO World Heritage", "Aldeias Históricas de Portugal"]


def town_scores(chosen):
    """Score of each town: places with a quality marker count 1 (UNESCO and historic villages count 3),
    the others 0.1"""
    points = (1 + 2 * chosen["subcategory"].isin(SPECIAL)).where(chosen["quality_marker"] == True, 0.1)
    return points.groupby(chosen["municipality"]).sum().sort_values(ascending=False, kind="stable")


def beach_itinerary(chosen, coordinates, days, start=None):
    """Rule 2: one base town, a different beach every day (the closest first)"""
    scores = town_scores(chosen)
    base = start if start in scores.index else scores.index[0]
    base_lat, base_lon = coordinates.loc[base, ["latitude", "longitude"]]
    chosen = chosen.dropna(subset=["latitude"]).copy()
    chosen["km"] = [distance_km(base_lat, base_lon, lat, lon) for lat, lon in zip(chosen["latitude"], chosen["longitude"])]
    # The beaches of the base town first, then the closest ones in other towns
    chosen["other_town"] = chosen["municipality"] != base
    beaches = chosen.sort_values(["other_town", "km"]).drop_duplicates("name")
    near = beaches[beaches["km"] < MAX_BEACH_KM]
    beaches = near if len(near) > 0 else beaches.head(1)

    plan = []
    for day in range(days):
        beach = beaches.iloc[day % len(beaches)]          # if there are fewer beaches than days, we start again
        plan.append({"day": day + 1, "town": beach["municipality"],          # the town where the beach is
                     "places": beach["name"],
                     "latitude": beach["latitude"], "longitude": beach["longitude"],   # the beach, for the map
                     "note": f"🏖️ Beach day · stay in {base}"
                             + (f" ({beach['km']:.0f} km)" if beach["km"] >= 5 else "")})
    return plan


def trip_km(route, km):
    """Total distance of a round trip (km): through the towns in this order, and back to the start.
    km = table of distances"""
    return sum(km[route[i]][route[i + 1]] for i in range(len(route) - 1)) + km[route[-1]][route[0]]


def shortest_order(route, coordinates):
    """Rule 7: same towns, same start, shortest round trip (improved with "2-opt")."""
    # Table of distances between every 2 towns (computed only once, so it's fast)
    points = {town: coordinates.loc[town, ["latitude", "longitude"]].values for town in route}
    km = {a: {b: distance_km(*points[a], *points[b]) for b in route} for a in route}

    return improve_order(route, km)


def improve_order(route, km):
    """Method "2-opt": we take a piece of the route and turn it around; if the trip gets shorter, we keep it.
    We repeat until no change makes it shorter."""
    best = list(route)
    improved = True
    while improved:
        improved = False
        for i in range(1, len(best) - 1):
            for j in range(i + 1, len(best)):
                new = best[:i] + best[i:j + 1][::-1] + best[j + 1:]     # turn around the piece i..j
                if trip_km(new, km) < trip_km(best, km) - 0.01:
                    best, improved = new, True
    return best


def places_per_day(package):
    """Rule 5: number of places in one day (a mix trip with only beaches or parks: fewer)"""
    themes = theme_categories(package) if package["specialty"] == "mix" else [package["specialty"]]
    return max(PLACES_PER_DAY.get(theme, 3) for theme in themes)


def add_nearby(groups, route, chosen, coordinates, per_day, seen):
    """Rule 5: a town with fewer places than a day can hold gets places of the theme from the towns around it
    (less than 25 km away, not on the route), most important first. Returns {town: [nearby towns]}"""
    others = chosen[~chosen["municipality"].isin(route)].dropna(subset=["latitude"])
    nearby_towns = {}
    for town in route:
        missing = per_day - len(groups[town])
        if missing <= 0 or len(others) == 0:
            continue
        lat, lon = coordinates.loc[town, ["latitude", "longitude"]]
        km = [distance_km(lat, lon, a, b) for a, b in zip(others["latitude"], others["longitude"])]
        near = others.assign(km=km)
        near = near[near["km"] < NEARBY_KM].sort_values(["importance", "km"])
        for _, place in near.iterrows():
            english = english_name(place["name"])
            if missing > 0 and not any(english in other or other in english for other in seen):
                groups[town].append(place["name"])
                seen.add(english)
                nearby_towns.setdefault(town, []).append(place["municipality"])
                missing -= 1
    return {town: list(dict.fromkeys(names)) for town, names in nearby_towns.items()}


def road_trip(chosen, coordinates, days, gem=None, all_places=None, start=None, per_day=3):
    """Rule 3: start in the best town; each day, the best town less than 60 km away"""
    scores = town_scores(chosen)
    route = [start if start in scores.index else scores.index[0]]    # the tourist can choose where to start
    while len(route) < days and len(route) < len(scores):
        here = coordinates.loc[route[-1]]
        left = [town for town in scores.index if town not in route]
        km = {town: distance_km(here["latitude"], here["longitude"], *coordinates.loc[town, ["latitude", "longitude"]])
              for town in left}
        near = [town for town in left if km[town] < MAX_DAY_TRIP_KM]
        route.append(near[0] if near else min(km, key=km.get))   # near is already sorted by score

    # Rule 4: one day in the hidden gem (after the town of the route closest to it)
    if gem and gem not in route and days >= 5:
        gem_lat, gem_lon = coordinates.loc[gem, ["latitude", "longitude"]]
        closest = min(range(len(route)),
                      key=lambda i: distance_km(gem_lat, gem_lon, *coordinates.loc[route[i], ["latitude", "longitude"]]))
        route.insert(closest + 1, gem)
        route = route[:days]

    # Rule 7: the shortest order (no going back and forth)
    route = shortest_order(route, coordinates)

    # The places of each town, in groups of 3 (one group = one day)
    groups = {town: list(dict.fromkeys(mixed_order(chosen[chosen["municipality"] == town])))
              if chosen["category"].nunique() > 1 else list(chosen[chosen["municipality"] == town]["name"].drop_duplicates())
              for town in route if town in chosen["municipality"].values}
    groups.update({town: [] for town in route if town not in groups})
    if gem in groups and not groups[gem]:
        # The hidden gem may have no places of the theme: we show its best places with a quality marker
        gem_places = all_places[(all_places["municipality"] == gem) & (all_places["quality_marker"] == True)]
        gem_places = gem_places.assign(importance=gem_places["subcategory"].map(IMPORTANCE).fillna(5))
        groups[gem] = list(gem_places.sort_values("importance")["name"].drop_duplicates())
    # A big park can be in 2 towns (e.g. Peneda-Gerês): each place appears only once in the trip
    # The same place can have 2 names in the data (e.g. "Palácio Nacional de Mafra" and "... e tapada"):
    # we compare the English names
    seen = set()
    for town in route:
        unique = []
        for name in groups[town]:
            english = english_name(name)
            # skip it if we already have it (or a name that contains it, e.g. "Jerónimos Monastery and Belém Tower")
            if not any(english in other or other in english for other in seen):
                unique.append(name)
                seen.add(english)
        groups[town] = unique
    route = [town for town in route if groups[town]]      # a town with nothing new to see is skipped

    # Rule 5: complete the days with places in the towns around
    nearby = add_nearby(groups, route, chosen, coordinates, per_day, seen)

    def note(town):
        notes = ["💎 Hidden gem"] if town == gem else []
        if town in nearby:
            notes.append("📍 Also nearby: " + ", ".join(nearby[town]))
        return " · ".join(notes)

    plan = [{"town": town, "places": groups[town][:per_day], "note": note(town)} for town in route]
    used = {town: per_day for town in route}

    # Rule 6: more days than towns (e.g. on a small island) -> one more day in the town with the most
    # places still to see, right after its first day (so we don't go back and forth)
    while len(plan) < days:
        left = {town: len(groups[town]) - used[town] for town in route}
        town = max(left, key=left.get)
        if left[town] <= 0:     # nothing left to see: free day at the end
            plan.append({"town": route[0], "places": ["Free day: walk, eat, relax"], "note": "☕ Free day"})
            continue
        position = max(i for i, day in enumerate(plan) if day["town"] == town) + 1
        plan.insert(position, {"town": town, "places": groups[town][used[town]:used[town] + per_day],
                               "note": "🔁 More to see"})
        used[town] += per_day

    for number, day in enumerate(plan, start=1):
        day["day"] = number
        day["places"] = " · ".join(day["places"])
    return plan


def add_coordinates(plan, coordinates):
    """Latitude and longitude of each day (for the route map): the town, if the day doesn't have its own point"""
    for column in ["latitude", "longitude"]:
        town_value = plan["town"].map(coordinates[column])
        plan[column] = plan[column].fillna(town_value) if column in plan else town_value


def well_known(chosen, municipalities, region, island=None):
    """Rule 9: keep only the towns in the top 60% of the region (or island) by overnight stays"""
    towns = municipalities[municipalities["region"] == region].set_index("municipality")["stays_2025"]
    if island:
        towns = towns[towns.index.map(ISLANDS) == island]
    known = towns[towns >= towns.quantile(KNOWN_TOWNS)].index
    kept = chosen[chosen["municipality"].isin(known)]
    if len(kept) == 0:
        return chosen                             # if nothing is left, we keep all the towns
    points = town_scores(kept)
    strong = points[points >= MIN_POINTS * points.max()].index
    return kept[kept["municipality"].isin(strong)]


def build_itinerary(places, municipalities, package, days=7, island=None,
                    visited=(), busy=(), start=None):
    """Day-by-day plan for a package (one row per day).
    visited: towns the tourist already visited · busy: towns to skip if they prefer fewer tourists (rule 8)"""
    coordinates = municipalities.set_index("municipality")[["latitude", "longitude", "hidden_gem", "region"]]

    if package["region"] in ["Açores", "Azores", "Madeira"] and island is None:
        island = best_island(places, package)
    chosen = theme_places(places, package, island)

    # Rule 9: culture and mix trips go to well-known towns (not when the tourist prefers fewer tourists)
    if package["specialty"] in ["culture", "mix"] and len(busy) == 0:
        chosen = well_known(chosen, municipalities, package["region"], island)

    # Rule 8: skip the visited and the busy towns. If nothing is left, we skip only the visited ones;
    # if still nothing is left, we keep all the towns.
    skip_towns = list(visited) + list(busy)
    for skip in [skip_towns, list(visited)]:
        if len(chosen[~chosen["municipality"].isin(skip)]) > 0:
            chosen = chosen[~chosen["municipality"].isin(skip)]
            break

    if package["specialty"] == "beach":
        plan = beach_itinerary(chosen, coordinates, days, start)
    else:
        # The hidden gem closest to the start (same region, same island, less than 150 km)
        scores = town_scores(chosen)
        start = start if start in scores.index else scores.index[0]
        gems = coordinates[(coordinates["hidden_gem"] == True) & (coordinates["region"] == package["region"])
                           & (~coordinates.index.isin(skip_towns))]
        if island:
            gems = gems[gems.index.map(ISLANDS) == island]
        gem = None
        if len(gems) > 0:
            km = {g: distance_km(*coordinates.loc[start, ["latitude", "longitude"]], *gems.loc[g, ["latitude", "longitude"]])
                  for g in gems.index}
            closest = min(km, key=km.get)
            gem = closest if km[closest] < MAX_GEM_KM else None
        plan = road_trip(chosen, coordinates, days, gem, places, start, places_per_day(package))

    plan = pd.DataFrame(plan)
    plan["island"] = island
    # The map point of each day: the main place of the day (so 3 days in the same town are 3 different pins);
    # if the place has no coordinates, the town
    points = places.dropna(subset=["latitude"]).drop_duplicates(["municipality", "name"]).set_index(["municipality", "name"])
    main_place = [(town, text.split(" · ")[0]) for town, text in zip(plan["town"], plan["places"])]
    for column in ["latitude", "longitude"]:
        place_value = pd.Series([points[column].get(key) for key in main_place], index=plan.index, dtype=float)
        plan[column] = plan[column].fillna(place_value) if column in plan else place_value
    add_coordinates(plan, coordinates)
    return plan


def busiest_towns(municipalities, month_pct, region, month):
    """The busiest half of the towns of a region in a month (overnight stays in that month)"""
    towns = municipalities[municipalities["region"] == region].set_index("municipality")["stays_2025"]
    in_month = towns * month_pct.reindex(towns.index)[month] / 100
    return list(in_month[in_month >= in_month.median()].index)


# Order of the traditional dishes: the winners of the "7 Maravilhas da Gastronomia" first, then the finalists
RESULT_ORDER = {"Winner": 0, "Finalist": 1, "Candidate": 2}


def trip_food(dishes, products, region, towns, how_many=None):
    """What to try on each day of the trip, WITHOUT REPEATING anything in the same trip:
    1. the dishes with the name of the town of the day (e.g. "Alheira de Mirandela" in Mirandela)
    2. the other traditional dishes of the region (winners first)
    3. when there are no more dishes: the local products with a protected name (DOP / IGP)
    towns = the town of each day. how_many = things per day (by default 2, or 1 if the region has few,
    so every day gets something). Returns one text per day (empty if there is nothing new left)."""
    region_dishes = dishes[dishes["region"] == region].copy()
    region_dishes["order"] = region_dishes["result"].map(RESULT_ORDER)
    region_dishes = region_dishes.sort_values("order", kind="stable")
    names = [re.sub(r"\s*\(.*\)", "", dish) for dish in region_dishes["dish"]]   # "Alheira de Mirandela (IG)" -> without "(IG)"
    # one product of each type first (cheese, honey, olive oil...), so the products are varied
    region_products = products[products["region"] == region]
    region_products = pd.concat([region_products.drop_duplicates("category"),
                                 region_products[region_products.duplicated("category")]])
    names += [re.split(r"\s*/\s*", product)[0].strip() for product in region_products["product"]]
    names = list(dict.fromkeys(names))          # no duplicates

    if how_many is None:
        how_many = 2 if len(names) >= 2 * len(towns) else 1
    used, food = set(), []
    for town in towns:
        local = [name for name in names if town.split(" (")[0] in name and name not in used]
        others = [name for name in names if name not in local and name not in used]
        today = (local + others)[:how_many]
        used.update(today)
        food.append(", ".join(today))
    return food
