"""
Discover Portugal – Plan my trip 🇵🇹
-----------------------------------
A Streamlit app with 3 tabs:
  🧭 Plan my trip          → the tourist chooses the type of trip, the month and the number of days,
                             and gets the package, a day-by-day itinerary (with photos), when to go and a map
  📍 My Portugal           → the places the tourist has already visited, as pins on a map
                             (the itineraries skip them)
  🌍 For travel agencies   → the agency chooses a country,
                             and sees which packages to sell there (preference index)

All the data comes from the notebooks (data/clean).
Run it with:   streamlit run app/app.py
"""

import base64
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

import altair as alt
import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

# The itinerary rules are in app/itinerary.py (the same code as notebook 03)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from english import english_foods, english_name, english_region
from itinerary import (ISLANDS, NATURE_HIGHLIGHTS, build_itinerary, busiest_towns, start_options,
                       theme_places, tourist_places, trip_food)

# ------------------------------------------------------------------
# 0. Settings
# ------------------------------------------------------------------
st.set_page_config(page_title="Discover Portugal", page_icon="🇵🇹", layout="wide")

# The data is in the "data/clean" folder, next to the "app" folder
DATA = Path(__file__).resolve().parent.parent / "data" / "clean"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]

# Colours (the same as the presentation)
NAVY, RED, SAND, CREAM = "#12304A", "#B5482F", "#D9CBB5", "#F7F2E8"
THEME_COLOURS = {"beach": "#2E6DB4", "culture": "#B5482F", "countryside": "#C9A227",
                 "nature": "#2E8B57", "viewpoint": "#7A6FB0", "mix": "#D9822B"}

# Mix trips: the tourist chooses what to mix
MIX_OPTIONS = {"🏛️ Culture": "culture", "🏖️ Beach": "beach", "🌲 Nature": "nature",
               "🏡 Historic villages": "countryside", "🔭 Viewpoints": "viewpoint"}

# Type of trip -> the specialty of the region (notebook 03) and the places we show
TRIPS = {
    "🏖️ Beach": {"specialty": "beach", "categories": ["beach"]},
    "🏛️ Culture": {"specialty": "culture", "categories": ["culture"]},
    "🏡 Historic villages": {"specialty": "countryside", "categories": ["countryside"]},
    "🌲 Nature": {"specialty": "nature", "categories": ["nature"]},
    "🔭 Viewpoints": {"specialty": "viewpoint", "categories": ["nature", "viewpoint"]},
    "🎨 Mix": {"specialty": "mix", "categories": None},          # the tourist chooses (question 2)
}

# Which places to show first (lower number = more important)
IMPORTANCE = {"UNESCO World Heritage": 0,
              "National Monument": 1, "Aldeias Históricas de Portugal": 1, "Aldeias do Xisto": 1,
              "museum": 2}

# A bit of style: fonts and colours of the presentation
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;700&family=Playfair+Display:wght@700&display=swap');
html, body, [class*="css"], .stMarkdown, p, li, label { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'Playfair Display', Georgia, serif !important; color: #12304A; }
.hero { background: #12304A; color: #F7F2E8; border-radius: 20px; padding: 36px 40px; margin-bottom: 8px; }
.hero h1 { color: #F7F2E8 !important; font-size: 52px; margin: 0; }
.hero p { color: #DCE6EE; font-size: 20px; margin: 8px 0 0 0; }
.card { border-radius: 18px; padding: 24px 28px; background: #FFFDF8; border: 1px solid #E6DCC8; }
.card h2 { margin: 0 0 4px 0; font-size: 36px; }
.tag { display: inline-block; border-radius: 999px; padding: 4px 14px; margin: 4px 6px 0 0;
       font-size: 15px; font-weight: 700; color: white; }
.stop { border-radius: 16px; padding: 16px 18px; background: #FFFDF8; border: 1px solid #E6DCC8; height: 100%; }
.stop b { color: #B5482F; }
.day { border-radius: 14px; padding: 12px 16px; background: #FFFDF8; border: 1px solid #E6DCC8; margin-bottom: 10px; }
.day h4 { margin: 2px 0 4px 0; font-family: 'DM Sans', sans-serif !important; }
.day img { width: 100%; height: 130px; object-fit: cover; border-radius: 10px; margin-bottom: 8px; }
.hero-photo { width: 100%; height: 260px; object-fit: cover; border-radius: 18px; }
/* our cards are always light, so their text is always dark (also in dark mode) */
.card, .stop, .day, .card p, .card li, .stop p, .stop li, .day p, .day li, .day h4, .card h2 { color: #12304A; }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------
# 1. Load the data (only once, Streamlit keeps it in memory)
# ------------------------------------------------------------------
def data_version():
    """The last time the data files changed: when we run a notebook again, the app loads the new data"""
    return max(file.stat().st_mtime for file in DATA.glob("*.csv"))


@st.cache_data
def load_data(version):
    places = pd.read_csv(DATA / "places.csv")
    # Viewpoints with a number (e.g. "Miradouro das Veredas 1" and "2"): we drop the number,
    # so the trip shows "Viewpoint of Veredas" only once (the itinerary skips repeated names)
    is_viewpoint = places["name"].str.startswith("Miradouro", na=False)
    places.loc[is_viewpoint, "name"] = places.loc[is_viewpoint, "name"].str.replace(r"\s+\d+$", "", regex=True)
    municipalities = pd.read_csv(DATA / "tableau_municipalities.csv")
    # Places without coordinates (e.g. the villages): we use the coordinates of their municipality
    centre = municipalities.set_index("municipality")
    places["latitude"] = places["latitude"].fillna(places["municipality"].map(centre["latitude"]))
    places["longitude"] = places["longitude"].fillna(places["municipality"].map(centre["longitude"]))

    month_pct = pd.read_csv(DATA / "municipality_month_pct.csv").set_index("municipality")
    # Overnight stays of each town in each month = stays of the year × % of the year in that month
    stays = municipalities.set_index("municipality")["stays_2025"]
    month_stays = month_pct.mul(stays.reindex(month_pct.index), axis=0) / 100
    # Each town compared with the other towns of its region: 0 = the quietest, 1 = the busiest
    region = municipalities.set_index("municipality")["region"].reindex(month_stays.index)
    crowd_rank = month_stays.groupby(region).rank(pct=True)
    region_month = pd.read_csv(DATA / "tableau_region_month.csv")
    region_country = pd.read_csv(DATA / "tableau_region_country.csv")
    packages = pd.read_csv(DATA / "packages.csv")
    dishes = pd.read_csv(DATA / "traditional_dishes.csv")
    products = pd.read_csv(DATA / "food_products.csv")
    # The app is in English: region names in English ("Norte" -> "North"); the municipalities stay in Portuguese
    for table in [places, municipalities, region_month, region_country, packages, dishes, products]:
        table["region"] = table["region"].map(english_region)
    return places, municipalities, month_pct, crowd_rank, region_month, region_country, packages, dishes, products


(places, municipalities, month_pct, crowd_rank, region_month, region_country, packages, dishes,
 products) = load_data(data_version())


# ------------------------------------------------------------------
# 2. Helper functions
# ------------------------------------------------------------------
def crowd_level(municipality, month):
    """How busy is a town in a month, compared with the other towns of its region?
    🔴 the busiest 25% · 🟡 the next 25% · 🟢 the quietest half"""
    if municipality not in crowd_rank.index or pd.isna(crowd_rank.loc[municipality, month]):
        return "⚪ no data"
    rank = crowd_rank.loc[municipality, month]
    if rank > 0.75:
        return "🔴 busy"
    if rank > 0.5:
        return "🟡 normal"
    return "🟢 quiet"


@st.cache_data(show_spinner=False)
def photo(title):
    """A photo from Wikipedia (Portuguese, then English). Returns None if there is no photo or no internet."""
    for language in ["pt", "en"]:
        try:
            url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}"
            page = requests.get(url, timeout=4, headers={"User-Agent": "DiscoverPortugal/1.0 (student project)"}).json()
            if page.get("type") == "standard" and "thumbnail" in page:
                return page["thumbnail"]["source"].replace("/320px-", "/640px-")
        except Exception:
            pass
    return None


@st.cache_data(show_spinner=False)
def commons_photo(search):
    """The first photo (JPG) found on Wikimedia Commons for a search, e.g. "Praia da Marinha Lagoa" """
    try:
        answer = requests.get("https://commons.wikimedia.org/w/api.php", timeout=4,
                              headers={"User-Agent": "DiscoverPortugal/1.0 (student project)"},
                              params={"action": "query", "format": "json", "generator": "search",
                                      "gsrsearch": search, "gsrnamespace": 6, "gsrlimit": 8,
                                      "prop": "imageinfo", "iiprop": "url|mime", "iiurlwidth": 640}).json()
        pages = sorted(answer.get("query", {}).get("pages", {}).values(), key=lambda page: page["index"])
        for page in pages:
            info = page["imageinfo"][0]
            if info["mime"] == "image/jpeg":
                return info["thumburl"]
    except Exception:
        pass
    return None


# Our own photos: put them in the folder app/photos, with the name of the place or of the town
# (e.g. "Monsanto.jpg", "Praia da Marinha.jpg", "Óbidos.jpg"). They come first, before the internet photos.
APP_FOLDER = Path(__file__).resolve().parent
PHOTOS = APP_FOLDER / "photos" if (APP_FOLDER / "photos").exists() else APP_FOLDER / "Photos"


PHOTO_TYPES = {".jpg": "jpeg", ".jpeg": "jpeg", ".jfif": "jpeg", ".png": "png", ".webp": "webp"}

# Photos saved with the English name of the town
PHOTO_OTHER_NAMES = {"lisboa": "lisbon"}

# Photos of a famous place: the town where it is (e.g. "Benagil.jfif" is a photo for Lagoa)
PHOTO_PLACES = {"lisbon": "Lisboa", "belem": "Lisboa", "jeronimos": "Lisboa",
                "monsaraz": "Reguengos de Monsaraz", "monzaras": "Reguengos de Monsaraz",
                "cacela": "Vila Real de Santo António", "benagil": "Lagoa (Algarve)", "monsanto": "Idanha-a-Nova",
                "terra nostra": "Povoação", "terr nostra": "Povoação", "furnas": "Povoação",
                "flores": "Santa Cruz das Flores", "berlengas": "Peniche",
                "madeira market": "Funchal", "caves porto": "Vila Nova de Gaia"}


def simple(text):
    """Lower case and without accents, to compare names ("Óbidos" -> "obidos")"""
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower().strip()


def photos_version():
    """Changes when we add or change a photo, so the app finds the new photos"""
    # names + dates: renaming a photo also counts as a change
    return str(sorted((f.name, f.stat().st_mtime) for f in PHOTOS.iterdir())) if PHOTOS.exists() else ""


@st.cache_data(show_spinner=False)
def own_photo_cached(name, version):
    """Our own photo for this name, ready to show in the page. None if there is none.
    The file name can be:  "Óbidos.jpg"  or  "Porto — Ribeira.jfif"  or  "Santa Cruz das Flores, Portugal.jfif"
    (the name of the place, and after it, optional: " — ", ", " or " (" and any text)"""
    if not PHOTOS.exists():
        return None
    names = [simple(name)] + ([PHOTO_OTHER_NAMES[simple(name)]] if simple(name) in PHOTO_OTHER_NAMES else [])
    for file in sorted(PHOTOS.iterdir()):
        kind = PHOTO_TYPES.get(file.suffix.lower())
        if kind is None:
            continue
        stem = simple(file.stem)
        # "Rocha Baixinha Beach.jfif" or "Praia da Rocha Baixinha.jfif" is also a photo of "Rocha Baixinha"
        stems = {stem, re.sub(r"\s+beach$", "", stem), re.sub(r"^praia( d[aeo]s?)? ", "", stem)}
        for n in names:
            for st_ in stems:
                if st_ == n or re.match(rf"{re.escape(n)}\s*[—–,(\-_]", st_):
                    return f"data:image/{kind};base64," + base64.b64encode(file.read_bytes()).decode()
    return None


def own_photo(name):
    return own_photo_cached(name, photos_version())


@st.cache_data(show_spinner=False)
def town_photo_files(version):
    """{town: [photo files]}: a photo belongs to a town if the town's name is in the file name
    (e.g. "Evora Templo Diana.jpg" -> Évora, "Porto Santo island.jfif" -> Porto Santo, not Porto),
    or the name of a famous place of the town (PHOTO_PLACES, e.g. "Benagil" -> Lagoa)"""
    if not PHOTOS.exists():
        return {}
    towns = sorted(municipalities["municipality"], key=len, reverse=True)     # longest names first
    found = {}
    for file in sorted(PHOTOS.iterdir()):
        if file.suffix.lower() not in PHOTO_TYPES:
            continue
        stem = simple(file.stem)
        town = next((t for t in towns
                     if re.search(rf"(?<![a-z]){re.escape(simple(t.split(' (')[0]))}(?![a-z])", stem)), None)
        town = town or next((t for key, t in PHOTO_PLACES.items() if key in stem), None)
        if town:
            found.setdefault(town, []).append(file)
    return found


# Photos of food: the start of the file name -> words of the dishes it can show
# (e.g. "Sardinhas.jfif" for "Sardinha assada", "Pastel de nata.jfif" for "Pastel de Belém")
FOOD_PHOTOS = {"sardinha": ["sardinha"], "bacalhau a bras": ["bacalhau a bras", "bacalhau a braz"],
               "caldo verde": ["caldo verde"], "cozido": ["cozido"], "francesinha": ["francesinha"],
               "pastel de nata": ["pastel de nata", "pastel de belem"], "queijo da serra": ["serra da estrela"],
               "vinho douro": ["vinho do porto", "vinho do douro"], "cataplana": ["cataplana"],
               "sopa da pe": ["sopa da pedra"]}

# Photos with only the name of a region (e.g. "Algarve.jfif", "Açores 1.jfif"): the last option for a day
REGION_PHOTOS = {"acores": "Azores", "azores": "Azores", "alentejo": "Alentejo", "algarve": "Algarve",
                 "madeira": "Madeira", "lisbon": "Lisbon", "norte": "North", "centro": "Centre"}


def food_photo(dishes_of_day):
    """Our own photo of the dish of the day (used when we have no photo of the place or the town)"""
    if not PHOTOS.exists() or not dishes_of_day:
        return None
    dishes = simple(dishes_of_day)
    for file in sorted(PHOTOS.iterdir()):
        if file.suffix.lower() not in PHOTO_TYPES:
            continue
        for start, words in FOOD_PHOTOS.items():
            if simple(file.stem).startswith(start) and any(word in dishes for word in words):
                return f"data:image/{PHOTO_TYPES[file.suffix.lower()]};base64," + base64.b64encode(file.read_bytes()).decode()
    return None


def region_photo(region, number=0):
    """Our own photo of the region (only photos that are not of a town), for days without any other photo"""
    if not PHOTOS.exists():
        return None
    town_files = {file for files in town_photo_files(photos_version()).values() for file in files}
    files = [file for file in sorted(PHOTOS.iterdir())
             if file.suffix.lower() in PHOTO_TYPES and file not in town_files
             and any(simple(file.stem).startswith(key) and name == region for key, name in REGION_PHOTOS.items())]
    if not files:
        return None
    file = files[number % len(files)]
    return f"data:image/{PHOTO_TYPES[file.suffix.lower()]};base64," + base64.b64encode(file.read_bytes()).decode()


def town_photo(town, number=0):
    """Our own photo of a town (no internet photos). number: the 2nd day in the same town gets the 2nd photo"""
    files = town_photo_files(photos_version()).get(town, [])
    if not files:
        return None
    file = files[number % len(files)]
    return f"data:image/{PHOTO_TYPES[file.suffix.lower()]};base64," + base64.b64encode(file.read_bytes()).decode()


# Our own descriptions: app/descriptions.csv, with 2 columns: place, description. They come first.
DESCRIPTIONS = Path(__file__).resolve().parent / "descriptions.csv"

# What each type of place is, from our data (used when there is no other description)
PLACE_TYPES = {
    "UNESCO World Heritage": "🌍 UNESCO World Heritage site",
    "National Monument": "🏛️ National Monument",
    "Public Interest": "🏛️ Classified monument (public interest)",
    "Aldeias Históricas de Portugal": "🏰 One of the 12 Historic Villages of Portugal",
    "Aldeias do Xisto": "🪨 Schist village, in the mountains of the Centro",
    "museum": "🖼️ Museum",
    "beach": "🏖️ Blue Flag beach",
    "viewpoint": "🔭 Viewpoint",
}


@st.cache_data(show_spinner=False)
def own_descriptions():
    """Our own descriptions (if the file exists): {place: description}"""
    if not DESCRIPTIONS.exists():
        return {}
    table = pd.read_csv(DESCRIPTIONS)
    return {place.lower(): text for place, text in zip(table["place"], table["description"])}


@st.cache_data(show_spinner=False)
def wikipedia_text(place, town, region):
    """The first 2 sentences of the English Wikipedia page of the place (we try the English name, then the Portuguese one).
    To avoid a page about another place with the same name, the text must mention the town, the region or Portugal."""
    for title in dict.fromkeys([english_name(place), place]):
        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}"
            page = requests.get(url, timeout=4, headers={"User-Agent": "DiscoverPortugal/1.0 (student project)"}).json()
            text = page.get("extract", "")
            if page.get("type") == "standard" and any(word in text for word in [town.split(" (")[0], region, "Portugal"]):
                sentences = re.split(r"(?<=[.!?])\s+", text)
                return " ".join(sentences[:2])[:280]
        except Exception:
            pass
    return None


def english(place, town):
    """English name of a place of our data (we need its type to know if it's a beach)"""
    row = places[(places["name"] == place) & (places["municipality"] == town)]
    return english_name(place, row["category"].iloc[0] if len(row) > 0 else None)


def place_description(place, town):
    """Description of a place: 1. ours  2. Wikipedia  3. the type of place, from our data"""
    ours = own_descriptions().get(place.lower()) or own_descriptions().get(english(place, town).lower())
    if ours:
        return ours
    row = places[(places["name"] == place) & (places["municipality"] == town)]
    # A place can be in the data twice (e.g. a historic village that is also a monument): the most special first
    special_first = ["UNESCO World Heritage", "Aldeias Históricas de Portugal", "Aldeias do Xisto", "National Monument"]
    row = row.assign(rank=row["subcategory"].map({kind: i for i, kind in enumerate(special_first)}).fillna(99))
    row = row.sort_values("rank")
    region = row["region"].iloc[0] if len(row) > 0 else ""
    # Beaches: no Wikipedia (a beach often has the name of a village, e.g. "Parede", and the page is about the village)
    is_beach = len(row) > 0 and row["category"].iloc[0] == "beach"
    text = None if is_beach else wikipedia_text(place, town, region)
    if text:
        return text
    if len(row) > 0:
        kind = "beach" if row["category"].iloc[0] == "beach" else row["subcategory"].iloc[0]
        if row["category"].iloc[0] == "nature" and kind not in PLACE_TYPES:
            return "🌲 Protected natural area"
        return PLACE_TYPES.get(kind, "")
    return ""


def place_photo(place, town, beach=False, number=0):
    """Only our own photos (internet photos are often bad): 1. a photo of the place  2. a photo of the town"""
    search = place if not beach or place.lower().startswith("praia") else f"Praia {place}"
    return own_photo(place) or own_photo(search) or town_photo(town, number)


def day_photos(places_of_day, town, beach, dishes_of_day, region, is_free=False):
    """All the possible photos of a day, from the best to the worst (they are made one at a time, only if needed):
    our photos of the places, our photos of the town, internet photos, the dish of the day, the region"""
    if not is_free:
        for place in places_of_day:
            yield own_photo(place)
            if beach and not place.lower().startswith("praia"):
                yield own_photo(f"Praia {place}")
    for number in range(len(town_photo_files(photos_version()).get(town, []))):
        yield town_photo(town, number)
    # No photo of our own: a photo from the internet (Wikipedia, then Wikimedia Commons) of a place, then of the town
    if not is_free:
        for place in places_of_day:
            yield photo(place)
            yield commons_photo(f"{place} {town}")
    yield photo(town)
    yield food_photo(dishes_of_day)
    for number in range(10):
        yield region_photo(region, number)


def new_photo(photos, used):
    """The first photo that was not shown yet in the trip (None if all of them were already shown)"""
    for picture in photos:
        if picture and picture not in used:
            used.add(picture)
            return picture
    return None


def season_label(package, month):
    """High season, off-season tip or low season for this package and month"""
    if month in package["peak months"]:
        return "🔥 High season", "The most popular time: book early!"
    if month in package["off-season tip"]:
        return "🌿 Great choice", "Good weather and fewer tourists."
    return "🙂 Low season", "Very quiet: perfect for calm trips."


def months_chart(pct_by_month, month, colour):
    """Bar chart of the 12 months; the chosen month in colour"""
    data = pd.DataFrame({"month": MONTHS, "pct": pct_by_month})
    return (alt.Chart(data).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(x=alt.X("month:N", sort=MONTHS, title=None, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("pct:Q", title="% of the year's tourists"),
                    color=alt.condition(alt.datum.month == month, alt.value(colour), alt.value(SAND)),
                    tooltip=[alt.Tooltip("month:N", title="Month"), alt.Tooltip("pct:Q", title="% of the year", format=".1f")])
            .properties(height=260))


def route_map(plan, colour):
    """Map of the trip: a numbered circle for each stop and a line between them (in the order of the days)"""
    rgb = [int(colour[i:i + 2], 16) for i in (1, 3, 5)]          # "#B5482F" -> [181, 72, 47]
    points = plan.dropna(subset=["latitude"])

    # Days in the same place share one circle (e.g. "1, 2")
    stops = (points.groupby(["latitude", "longitude"], sort=False)
             .agg(label=("day", lambda days: ", ".join(map(str, days))), town=("town", "first"), places=("places", "first"))
             .reset_index())

    layers = []
    beach_trip = points["note"].str.contains("Beach day").any()
    if not beach_trip and points["town"].nunique() > 1:   # a road trip: draw the line (no line for the beach trip)
        path = points[["longitude", "latitude"]].values.tolist()
        line = [{"path": path}]          # from day 1 to the last day (the trip ends at the last stop)
        layers.append(pdk.Layer("PathLayer", line, get_path="path", get_color=rgb, width_min_pixels=4))
    layers.append(pdk.Layer("ScatterplotLayer", stops, get_position=["longitude", "latitude"], get_fill_color=rgb,
                            get_line_color=[255, 255, 255], stroked=True, line_width_min_pixels=2, radius_min_pixels=14,
                            pickable=True))
    layers.append(pdk.Layer("TextLayer", stops, get_position=["longitude", "latitude"], get_text="label",
                            get_color=[255, 255, 255], get_size=13, get_alignment_baseline="'center'"))

    # Zoom: the bigger the trip, the further away we look
    span = max(points["latitude"].max() - points["latitude"].min(), points["longitude"].max() - points["longitude"].min())
    zoom = 13 if span < 0.03 else 12 if span < 0.07 else 11 if span < 0.12 else 10 if span < 0.2 else 9 if span < 0.4 else 8 if span < 0.8 else 7 if span < 1.6 else 6
    view = pdk.ViewState(latitude=points["latitude"].mean(), longitude=points["longitude"].mean(), zoom=zoom)

    st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view, map_style=None,
                             tooltip={"text": "Day {label} · {town}\n{places}"}))


def show_itinerary(plan, colour, month):
    """Day cards (2 columns, with a photo of the main place of the day and the food to try) + a map of the trip"""
    region_of = municipalities.set_index("municipality")["region"]
    beach_trip = plan["note"].str.contains("Beach").any()
    # What to try each day, without repeating anything in the same trip
    food = trip_food(dishes, products, region_of[plan["town"].iloc[0]], list(plan["town"]))
    cards, map_column = st.columns([3, 2])
    used_photos = set()          # the photos already shown in this trip (so we never repeat one)
    with cards:
        columns = st.columns(2)
        for i, (_, day) in enumerate(plan.iterrows()):
            with columns[i % 2]:
                places_of_day = day["places"].split(" · ")
                main_place = places_of_day[0]
                is_free = main_place.startswith("Free day")
                town = day["town"]
                # The photo (only our own photos), NEVER the same photo twice in the trip:
                # 1. a photo of a place of the day (the 1st place, if none the 2nd, ...)  2. a photo of the town
                # 3. a photo of the dish of the day  4. a photo of the region
                picture = new_photo(day_photos(places_of_day, town, beach_trip, food[i], region_of[town],
                                               is_free), used_photos)
                image = f'<img src="{picture}" alt="{town}">' if picture else ""
                # What to see: one line per place (in English), the main place with a short description
                if is_free:
                    to_see = f"<li>{day['places']}</li>"
                else:
                    description = html.escape(place_description(main_place, town))
                    to_see = f"<li><b>{english(main_place, town)}</b><br><span style='color:#4A5563;'>{description}</span></li>"
                    to_see += "".join(f"<li>{english(other, town)}</li>" for other in places_of_day[1:])
                st.markdown(f"""
                <div class="day" style="border-left: 6px solid {colour};">
                  <p style="font-size:13px;letter-spacing:2px;color:#6B5E45;margin:0;">DAY {day['day']} &nbsp; {day['note']}</p>
                  <h4>📍 {town}</h4>
                  <p style="margin:0 0 6px 0;font-size:14px;">{crowd_level(town, month)}</p>
                  {image}
                  <ul style="margin:6px 0;padding-left:20px;font-size:14px;">{to_see}</ul>
                  <p style="margin:0;font-size:14px;">{"🍽️ <b>You must try:</b> " + english_foods(food[i]) if food[i] else ""}</p>
                </div>""", unsafe_allow_html=True)
    with map_column:
        # The map shows the English names too
        english_plan = plan.copy()
        english_plan["places"] = [places_text if places_text.startswith("Free day")
                                  else " · ".join(english(p, town) for p in places_text.split(" · "))
                                  for places_text, town in zip(plan["places"], plan["town"])]
        route_map(english_plan, colour)
        st.caption("🗺️ Your route: the numbers are the days · 🟢 quiet · 🟡 normal · 🔴 busy "
                   "(compared with the other towns of the region in that month)")


@st.cache_data
def region_shapes():
    """The 7 regions (from notebook 02), with fewer decimals so the map loads fast"""
    def round_coords(c):
        return [round_coords(x) for x in c] if isinstance(c[0], list) else [round(c[0], 3), round(c[1], 3)]
    with open(DATA / "tableau_regions.geojson", encoding="utf-8") as f:
        features = json.load(f)["features"]
    for feature in features:
        feature["geometry"]["coordinates"] = round_coords(feature["geometry"]["coordinates"])
        feature["properties"] = {"region": english_region(feature["properties"]["region"])}
        # Madeira: we drop the tiny Selvagens islands (far to the south), so Madeira looks bigger on the map
        if feature["properties"]["region"] == "Madeira" and feature["geometry"]["type"] == "MultiPolygon":
            feature["geometry"]["coordinates"] = [polygon for polygon in feature["geometry"]["coordinates"]
                                                  if polygon[0][0][1] > 31.5]
    return features


def region_picker(suggested, colour, islands_column, mainland_column, painted=None):
    """Map of the 7 regions, in two columns: the islands and the mainland.
    The tourist clicks the region they want. Returns the chosen region, or None (then we use the suggested one)."""
    shapes = alt.Data(values=region_shapes())
    chosen = st.session_state.get("map_choice")
    painted = chosen or painted      # the region of the trip is always in colour (clicked or suggested)
    turn = st.session_state.setdefault("map_turn", 0)     # a new turn = fresh maps (so every click counts)

    def view(regions, height, title, islands=False):
        pick = alt.selection_point(fields=["region"], name="pick", on="click")
        # the chosen region has the colour of the trip, the others are sand
        fill = alt.condition(alt.FieldEqualPredicate(field="region", equal=painted or ""),
                             alt.value(colour), alt.value(SAND))
        if islands:
            # the islands are tiny: a thin border of the same colour makes them a bit bigger and easier to click
            mark, outline = dict(strokeWidth=2.5, strokeJoin="round", cursor="pointer"), {"stroke": fill}
        else:
            mark, outline = dict(stroke="white", strokeWidth=1.5, cursor="pointer"), {}
        return (alt.Chart(shapes, title=title)
                .mark_geoshape(**mark)
                .transform_calculate(region="datum.properties.region")
                .transform_filter(alt.FieldOneOfPredicate(field="region", oneOf=regions))
                .encode(color=fill, **outline,
                        opacity=alt.condition(alt.FieldOneOfPredicate(field="region", oneOf=suggested),
                                              alt.value(1), alt.value(0.75)),
                        tooltip=alt.Tooltip("region:N", title="Region"))
                .project("mercator").properties(width="container", height=height)
                .add_params(pick).configure_view(stroke=None))

    maps = [(islands_column, "azores", view(["Azores"], 150, "Azores", islands=True)),
            (islands_column, "madeira", view(["Madeira"], 130, "Madeira", islands=True)),
            (mainland_column, "mainland", view(["North", "Centre", "Lisbon", "Alentejo", "Algarve"], 430, ""))]
    clicked = None
    for column, name, chart in maps:
        with column:
            try:   # clicking on a chart needs Streamlit 1.35 or newer
                event = st.altair_chart(chart, on_select="rerun", key=f"map_{name}_{turn}", use_container_width=True)
                selected = event["selection"]["pick"]
                if selected:
                    clicked = selected[0]["region"]
            except Exception:
                st.altair_chart(chart, use_container_width=True)

    if clicked:   # a new click: we remember it and draw fresh maps with the chosen region in colour
        st.session_state["map_choice"] = clicked
        st.session_state["map_turn"] = turn + 1
        st.rerun()
    if chosen:
        with mainland_column:
            if st.button("↺ Back to the suggestion"):
                st.session_state["map_choice"] = None
                st.session_state["map_turn"] = turn + 1
                st.rerun()
    return chosen


def best_destinations(trip_places, month, prefer_quiet, how_many=8):
    """Ranks municipalities by the number of places with a quality marker (skips the visited towns)"""
    trip_places = trip_places[~trip_places["municipality"].isin(st.session_state["visited"])]
    trip_places = trip_places.assign(english=[english_name(n, c) for n, c in zip(trip_places["name"], trip_places["category"])])
    summary = (trip_places.groupby("municipality")
               .agg(places=("name", "count"),
                    quality_places=("quality_marker", "sum"),
                    highlights=("english", lambda names: " · ".join(names.head(3))))
               .reset_index())
    summary = summary.merge(municipalities[["municipality", "region", "hidden_gem"]], on="municipality", how="left")
    summary["crowd"] = summary["municipality"].apply(lambda m: crowd_level(m, month))
    summary["gem"] = summary["hidden_gem"].map({True: "💎"}).fillna("")

    summary = summary.sort_values(["quality_places", "places"], ascending=False)
    if prefer_quiet:
        # Only the quiet towns (if there are any)
        quiet = summary[summary["crowd"] == "🟢 quiet"]
        summary = quiet if len(quiet) > 0 else summary
    return summary.head(how_many)


# ------------------------------------------------------------------
# 3. Header
# ------------------------------------------------------------------
total_stays = municipalities["stays_2025"].sum() / 1_000_000
st.markdown(f"""
<div class="hero">
  <h1>Discover Portugal</h1>
  <p>Let the data choose your next holiday · {total_stays:.0f} million overnight stays in 2025,
     {len(municipalities)} municipalities, {len(places):,} places</p>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# 3.1 Sidebar: where have you already been? (the itineraries skip these towns)
# ------------------------------------------------------------------
if "visited" not in st.session_state:
    st.session_state["visited"] = []


# Traveller levels: the more towns you visit, the higher your level (minimum number of towns for each level)
LEVELS = [(0, "🧳", "Dreamer"), (1, "🎒", "Traveller"), (10, "🧭", "Explorer"), (30, "🗺️", "Adventurer"),
          (80, "🏅", "Expert"), (150, "👑", "Master of Portugal"), (308, "🏆", "Legend")]


def traveller_level(n_towns):
    """The level for a number of visited towns, and the next level (None at the top)"""
    reached = [level for level in LEVELS if n_towns >= level[0]]
    current = reached[-1]
    following = LEVELS[len(reached)] if len(reached) < len(LEVELS) else None
    return current, following


def add_to_visited(towns):
    """Button "I did this trip": the towns of the itinerary go to the list of visited places"""
    st.session_state["visited"] = sorted(set(st.session_state["visited"]) | set(towns))


with st.sidebar:
    st.markdown("## 📍 Where have you been?")
    st.multiselect("Towns you already visited", sorted(municipalities["municipality"]), key="visited",
                   placeholder="e.g. Albufeira, Porto…")
    st.caption("We won't recommend these towns again. See your map in the **📍 My Portugal** tab.")
    n_visited = len(st.session_state["visited"])
    (minimum, icon, name), following = traveller_level(n_visited)
    st.markdown(f"### {icon} {name}")
    st.caption(f"{n_visited} of {len(municipalities)} towns visited")
    if following:
        # Progress to the next level
        done = (n_visited - minimum) / (following[0] - minimum)
        st.progress(done, text=f"{following[0] - n_visited} more to become {following[1]} {following[2]}")

tab_trip, tab_map, tab_agency = st.tabs(["🧭 Plan my trip", "📍 My Portugal", "🌍 For travel agencies"])

# ==================================================================
# TAB 1 – PLAN MY TRIP
# ==================================================================
with tab_trip:

    # 4. The 3 questions
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            trip = st.radio("**1. What kind of trip?**", list(TRIPS.keys()), horizontal=True)
        with col2:
            mix = None
            if trip == "🎨 Mix":   # only for mix: what do you want to mix?
                chosen_types = st.multiselect("**2. What do you want to mix?**", list(MIX_OPTIONS),
                                              default=["🏛️ Culture", "🏖️ Beach", "🌲 Nature"])
                mix = [MIX_OPTIONS[t] for t in chosen_types] or ["culture"]
            else:
                st.markdown("**2. What do you want to mix?**")
                st.caption("Only for mix trips")
        with col3:
            month_name = st.select_slider("**3. When do you want to go?**", options=MONTH_NAMES, value="June")
            month = MONTHS[MONTH_NAMES.index(month_name)]
            days = st.slider("**4. How many days?**", min_value=2, max_value=14, value=7)
            prefer_quiet = st.checkbox("I prefer places with fewer tourists 🤫",
                                       help="Skips the busiest half of the towns of the region in that month")

    # ------------------------------------------------------------------
    # 5. The package of the region and its itinerary
    # ------------------------------------------------------------------
    specialty = TRIPS[trip]["specialty"]
    colour = THEME_COLOURS[specialty]
    if specialty == "mix":
        # Mix: the 3 regions with the most quality places of the chosen types
        quality = places[(places["quality_marker"] == True) & (places["category"].isin(mix))]
        suggested = list(quality["region"].value_counts().index[:3])
    else:
        suggested = list(packages.loc[packages["specialty"] == specialty, "region"])   # regions with this specialty

    # 6.0 Where? A map of the regions: click one, or keep the region suggested by the data
    st.markdown("**5. Where?** Click a region")
    # three columns: the islands, the mainland and the options (the maps never cover the options)
    islands_column, mainland_column, choices = st.columns([1, 1, 1.4])
    clicked = st.session_state.get("map_choice")
    with choices:
        # The clicked region must have places of this kind (e.g. there are no historic villages in Lisboa)
        if clicked and len(theme_places(places, {"region": clicked, "specialty": specialty, "categories": mix})) == 0:
            st.warning(f"There are no places of this kind in {clicked}. Choose another region on the map.")
            clicked = st.session_state["map_choice"] = None
        if clicked:
            region = clicked
            st.success(f"📍 You chose **{region}**")
        else:
            region = st.radio("**Suggested for this trip:**", suggested, horizontal=True)
    # The map comes after the choices, so it can paint the region of the trip (the clicked or the suggested one)
    region_picker(suggested, colour, islands_column, mainland_column, painted=region)

    # The package of the region. If the trip is not the region's specialty (e.g. culture in Centro),
    # we keep the region's data (months, countries, gems) with the theme of the trip
    package = packages[packages["region"] == region].iloc[0].copy()
    own_specialty = package["specialty"] == specialty
    if not own_specialty:
        package["specialty"] = specialty
        package["package"] = f"{trip} · {region}"
        package["description"] = f"Discover {region} in a different way: the best {trip.split(' ', 1)[1].lower()} places of the region."
    if specialty == "mix":
        package["categories"] = mix
        package["description"] = f"A bit of everything in {region}: every day mixes " + \
            ", ".join(t.split(" ", 1)[1].lower() for t in chosen_types) + "."

    # Islands: the trip stays on one island (the tourist chooses it; first = the most places of the theme)
    island = None
    with choices:
        if region in ["Azores", "Madeira"]:
            islands = list(theme_places(places, package)["municipality"].map(ISLANDS).value_counts().index)
            # Beach in Madeira: the beach island is Porto Santo (9 km of golden sand);
            # the island of Madeira has cliffs and mountains, so a beach trip in Madeira goes only to Porto Santo
            if specialty == "beach" and "Porto Santo" in islands:
                islands = ["Porto Santo"]
            island = st.radio("**Which island?**", islands, horizontal=True)

        # Where to start (default: the best town of the theme; e.g. choose Óbidos to start there)
        # "Fewer tourists": the busiest half of the towns of the region in that month is not an option
        busy = busiest_towns(municipalities, month_pct, region, month) if prefer_quiet else []
        towns = start_options(places, package, island, list(st.session_state["visited"]) + busy)
        start = st.selectbox("**Start in** (or stay in, for the beach)", towns, index=0)
    season, season_text = season_label(package, month)

    # 6.1 The itinerary (we build it first, to show a photo of the first town on the card)
    plan = build_itinerary(places, municipalities, package, days, island,
                           visited=st.session_state["visited"], busy=busy, start=start)

    # 6.2 The package card
    card, numbers = st.columns([3, 2])
    with card:
        # The hidden gems of the region (on the islands: only the gems of the chosen island)
        region_gems = [] if package["hidden gems"] == "–" else [g.strip() for g in package["hidden gems"].split(",")]
        if island:
            region_gems = [g for g in region_gems if ISLANDS.get(g) == island]
        gems = "" if not region_gems else \
            f'<p style="font-size:17px;">💎 <b>Hidden gems to add:</b> {", ".join(region_gems)}</p>'
        st.markdown(f"""
        <div class="card" style="border-top: 8px solid {colour};">
          <p style="font-size:14px;letter-spacing:2px;color:#6B5E45;margin:0;">YOUR PACKAGE · {region.upper()}</p>
          <h2>{package['package']}</h2>
          <p style="font-size:18px;">{package['description']}</p>
          {gems}
          <p style="font-size:17px;">🍽️ <b>You must try:</b> {english_foods(package.get("you must try", "run notebook 03 to see the food"))}</p>
          <p style="font-size:17px;">🧀 <b>Take home:</b> {english_foods(package.get("local products", "–"))}</p>
          <span class="tag" style="background:{colour};">{season} in {month_name}</span>
          {f'<span class="tag" style="background:{NAVY};">Specialty: {package["specialty index"]:.1f}× the average</span>' if own_specialty else ""}
        </div>""", unsafe_allow_html=True)
    with numbers:
        first_place = plan["places"].iloc[0].split(" · ")[0]
        picture = place_photo(first_place, plan["town"].iloc[0], package["specialty"] == "beach")
        if picture:
            first_english = english(first_place, plan["town"].iloc[0])
            st.markdown(f'<img class="hero-photo" src="{picture}" alt="{first_english}">', unsafe_allow_html=True)
            st.caption(f"📷 {first_english}")

    # 6.3 The day-by-day itinerary
    st.subheader(f"🗓️ Your {days}-day itinerary" + (f" · {island}" if island else ""))
    if prefer_quiet:
        st.caption("🤫 Fewer tourists: we skip the busiest half of the towns of the region in " + month_name)
    show_itinerary(plan, colour, month)
    st.button("✅ I did this trip! Add these towns to my map", on_click=add_to_visited, args=(list(plan["town"]),))

    # 6.4 When to go + must-see places
    left, right = st.columns([3, 2])
    with left:
        st.subheader(f"📅 When to go to {region}")
        pct = (region_month[region_month["region"] == region].sort_values("month_number")["pct_of_year"].values)
        st.altair_chart(months_chart(pct, month, colour), use_container_width=True)
        st.caption("% of the region's overnight stays in each month · INE, 2025")
    with right:
        st.subheader("⭐ Must-see")
        # The 4 best places of this trip in the region (one per town)
        best = theme_places(places, package, island).drop_duplicates("municipality").head(4)
        for _, place in best.iterrows():
            st.markdown(f"- **{english_name(place['name'], place['category'])}** ({place['municipality']})")

    # 6.5 Places of this type of trip in the region (or island)
    trip_places = tourist_places(places)      # only places that interest tourists (see itinerary.py)
    trip_places = trip_places[(trip_places["category"].isin(mix or TRIPS[trip]["categories"]))
                              & (trip_places["region"] == region)]
    if island:
        trip_places = trip_places[trip_places["municipality"].map(ISLANDS) == island]

    # Most important places first (UNESCO, National Monuments, villages, parks…), then other quality places
    trip_places = trip_places.assign(importance=trip_places["subcategory"].map(IMPORTANCE).fillna(5))
    trip_places.loc[trip_places["name"].str.contains(NATURE_HIGHLIGHTS, na=False), "importance"] = 1
    trip_places = trip_places.sort_values(["importance", "quality_marker"], ascending=[True, False])

    # 6.6 Other destinations: table + map
    st.subheader(f"📍 More destinations in {month_name}")
    top = best_destinations(trip_places, month, prefer_quiet)
    if len(top) == 0:     # the tourist already visited all of them!
        st.success("🏆 You've already visited every destination of this kind here. Try another region on the map!")
        top = trip_places.head(0).assign(gem="", crowd="", quality_places=0, highlights="")
    table, mapping = st.columns([3, 2])
    with table:
        st.dataframe(
            top[["gem", "municipality", "crowd", "quality_places", "highlights"]],
            column_config={
                "gem": st.column_config.TextColumn("", width="small"),
                "municipality": "Destination",
                "crowd": f"Crowd in {month}",
                "quality_places": st.column_config.ProgressColumn(
                    "Top places", format="%d", min_value=0, max_value=int(top["quality_places"].max()) if len(top) > 0 else 1),
                "highlights": "Highlights",
            },
            hide_index=True, use_container_width=True)
        st.caption("🟢 quiet · 🟡 normal · 🔴 busy (compared with the other towns of the region, INE 2025) · 💎 hidden gem")
    with mapping:
        on_map = trip_places[trip_places["municipality"].isin(top["municipality"])].dropna(subset=["latitude"]).copy()
        if len(on_map) > 0:
            # Places in a hidden gem in red, the others in the colour of the package
            gem_towns = municipalities.loc[municipalities["hidden_gem"] == True, "municipality"]
            on_map["colour"] = on_map["municipality"].isin(gem_towns).map({True: RED, False: colour})
            st.map(on_map, latitude="latitude", longitude="longitude", size=80, color="colour")
        else:
            st.info("No places with coordinates for this choice.")

    with st.expander("See all the places"):
        all_places = on_map.assign(
            name=[english_name(n, c) for n, c in zip(on_map["name"], on_map["category"])],
            subcategory=[PLACE_TYPES.get("beach" if c == "beach" else t, t) for t, c in
                         zip(on_map["subcategory"], on_map["category"])])
        st.dataframe(all_places[["name", "municipality", "subcategory", "quality_marker"]].rename(columns={
            "name": "Place", "municipality": "Municipality", "subcategory": "Type",
            "quality_marker": "Official quality mark"}), hide_index=True, use_container_width=True)

# ==================================================================
# TAB 2 – MY PORTUGAL: the places I've been
# ==================================================================
with tab_map:
    visited = municipalities[municipalities["municipality"].isin(st.session_state["visited"])]
    st.subheader("📍 My Portugal")

    (minimum, icon, name), following = traveller_level(len(visited))
    if len(visited) == len(municipalities):
        # All the 308 towns: the top level! (balloons only once)
        if not st.session_state.get("celebrated"):
            st.balloons()
            st.session_state["celebrated"] = True
        st.markdown(f"""
        <div class="hero" style="background:{RED};text-align:center;">
          <h1>🏆 WELL DONE!</h1>
          <p>You visited all the {len(municipalities)} municipalities of Portugal. You reached the maximum level: <b>Legend</b>.</p>
        </div>""", unsafe_allow_html=True)
    elif len(visited) == 0:
        st.info("Add the towns you've visited in the sidebar on the left (or with the ✅ button after an itinerary), "
                "and they appear here as pins 📍")
    else:
        st.markdown(f"""
        <div class="card" style="border-top: 8px solid {RED};">
          <p style="font-size:14px;letter-spacing:2px;color:#6B5E45;margin:0;">YOUR LEVEL</p>
          <h2>{icon} {name}</h2>
          <p style="font-size:17px;">Next level: <b>{following[1]} {following[2]}</b>
             at {following[0]} towns · {following[0] - len(visited)} to go!</p>
        </div>""", unsafe_allow_html=True)

    # All the levels, to see what's next
    with st.expander("🏅 All the levels"):
        for level_minimum, level_icon, level_name in LEVELS:
            reached = "✅" if len(visited) >= level_minimum else "⬜"
            st.markdown(f"{reached} {level_icon} **{level_name}** · {level_minimum}+ towns")

    if len(visited) > 0:
        # Numbers: towns, % of Portugal, regions
        a, b, c = st.columns(3)
        a.metric("Towns visited", f"{len(visited)} of {len(municipalities)}")
        b.metric("Of Portugal", f"{len(visited) / len(municipalities):.0%}")
        c.metric("Regions", f"{visited['region'].nunique()} of 7")

    # Map: all the towns in grey, the visited ones as big red pins
    all_towns = municipalities.dropna(subset=["latitude"]).copy()
    all_towns["visited"] = all_towns["municipality"].isin(st.session_state["visited"])
    layers = [
        pdk.Layer("ScatterplotLayer", all_towns[~all_towns["visited"]], get_position=["longitude", "latitude"],
                  get_fill_color=[160, 150, 130, 120], radius_min_pixels=3, pickable=True),
        pdk.Layer("ScatterplotLayer", all_towns[all_towns["visited"]], get_position=["longitude", "latitude"],
                  get_fill_color=[181, 72, 47], get_line_color=[255, 255, 255], stroked=True,
                  line_width_min_pixels=2, radius_min_pixels=10, pickable=True),
    ]
    view = pdk.ViewState(latitude=39.6, longitude=-12.0, zoom=5.2)     # mainland + islands
    st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view, map_style=None,
                             tooltip={"text": "{municipality} · {region}"}), height=560)

    # Progress by region
    if len(visited) > 0:
        st.markdown("#### Your progress by region")
        totals_by_region = municipalities.groupby("region")["municipality"].count()
        done_by_region = visited.groupby("region")["municipality"].count().reindex(totals_by_region.index).fillna(0)
        columns = st.columns(len(totals_by_region))
        for column, region_name in zip(columns, totals_by_region.index):
            with column:
                share = done_by_region[region_name] / totals_by_region[region_name]
                st.markdown(f"**{region_name}**" + (" ✅" if share == 1 else ""))
                st.progress(float(share), text=f"{int(done_by_region[region_name])}/{totals_by_region[region_name]}")

# ==================================================================
# TAB 3 – FOR TRAVEL AGENCIES
# ==================================================================
with tab_agency:
    st.subheader("Which packages should we sell in each country?")
    st.write("The **preference index** compares the share of a country's tourists in a region with its share in Portugal. "
             "**2.0×** = this country likes the region twice as much as the average foreign tourist.")

    # Only countries with at least 500 000 stays (the same rule as the notebooks)
    totals = region_country.groupby("country")["overnight_stays"].sum()
    countries = totals[totals >= 500_000].sort_values(ascending=False).index
    country = st.selectbox("**Clients from:**", list(countries))

    ranking = (region_country[region_country["country"] == country]
               .merge(packages[["region", "package", "off-season tip", "when to sell"]], on="region")
               .sort_values("preference_index", ascending=False))
    best = ranking.iloc[0]

    left, right = st.columns([2, 3])
    with left:
        st.markdown(f"""
        <div class="card" style="border-top: 8px solid {RED};">
          <p style="font-size:14px;letter-spacing:2px;color:#6B5E45;margin:0;">BEST PACKAGE FOR {country.upper()}</p>
          <h2>{best['package']}</h2>
          <p style="font-size:20px;"><b>{best['region']}</b> · {best['preference_index']:.1f}× the average</p>
          <p style="font-size:17px;">🌿 Best time to travel: <b>{best['off-season tip']}</b> (fewer tourists)</p>
          <p style="font-size:17px;">📣 When to sell: <b>{best['when to sell']}</b> (3 months before the trip)</p>
          <p style="font-size:17px;">👥 {totals[country]:,.0f} overnight stays in Portugal in 2025</p>
        </div>""", unsafe_allow_html=True)
    with right:
        chart = (alt.Chart(ranking).mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
                 .encode(y=alt.Y("region:N", sort="-x", title=None),
                         x=alt.X("preference_index:Q", title="Preference index"),
                         color=alt.condition(alt.datum.preference_index >= 1, alt.value(RED), alt.value(SAND)),
                         tooltip=[alt.Tooltip("package:N", title="Package"),
                                  alt.Tooltip("preference_index:Q", title="Index", format=".2f")])
                 .properties(height=300))
        average = alt.Chart(pd.DataFrame({"x": [1]})).mark_rule(color=NAVY, strokeDash=[4, 4]).encode(x="x:Q")
        st.altair_chart(chart + average, use_container_width=True)
        st.caption("Red = more than average (dashed line = 1.0) · INE, 2025")

    st.dataframe(ranking[["package", "region", "preference_index", "off-season tip", "when to sell"]],
                 column_config={"package": "Package", "region": "Region",
                                "preference_index": st.column_config.NumberColumn("Preference index", format="%.1f×"),
                                "off-season tip": "Best time to travel", "when to sell": "When to sell"},
                 hide_index=True, use_container_width=True)

st.divider()
st.caption("Data: INE (overnight stays), ABAAE Blue Flag 2026, Wikidata, OpenStreetMap, Wikipedia · "
           "Final Project – Ironhack Data Analytics · Raquel Marques")
