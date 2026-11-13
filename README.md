# 🇵🇹 Discover Portugal: Data-Driven Travel Packages

*Where should you go on your next holiday? Let the data plan your trip.*

Final Project · Ironhack Data Analytics · Raquel Marques

| | Link |
|---|---|
| 📊 Tableau dashboard | [add link] |
| 🧭 Streamlit app – *Plan my trip* | [add link] |
| 🎤 Presentation | [add link] |

---

## 💡 The idea

Let's find out what the data tells us about tourism in Portugal, and use it to create **standard and personalised travel packages**, and to find out **in which countries we should sell each one**.

## ❓ The 5 questions

| # | Question |
|---|---|
| 1 | **Where** do tourists go? |
| 2 | **When** do they go? |
| 3 | **Who** visits each region? *(the key question: where to sell)* |
| 4 | **Beach, city, countryside or forest?** What does each place offer? |
| 5 | **Hidden gems:** which places have a lot to offer and few tourists? |

---

## 📂 Data

All the data is open. Full list with links and download dates: [`data/raw/SOURCES.md`](data/raw/SOURCES.md)

| Topic | Source |
|---|---|
| Overnight stays by municipality, month and country of residence | INE – Statistics Portugal (API) |
| Blue Flag beaches 2026 | ABAAE – Bandeira Azul |
| Classified monuments, protected areas, municipality coordinates | Wikidata |
| Museums and viewpoints | OpenStreetMap (Overpass API) |
| Historic and schist villages, DOP/IGP products, traditional dishes (7 Maravilhas) | Wikipedia |

---

## 🔬 Method (notebooks)

| Notebook | What it does |
|---|---|
| [`01_data_cleaning.ipynb`](notebooks/01_data_cleaning.ipynb) | Cleans all sources, gives every place a municipality (nearest known place, chosen after comparing 5 models: ~93% right), builds one table of places |
| [`02_statistics.ipynb`](notebooks/02_statistics.ipynb) | Answers Q1–Q5 with charts and 4 hypothesis tests (Kruskal-Wallis, Mann-Whitney U, Chi-square + Cramér's V, Spearman) |
| [`03_packages.ipynb`](notebooks/03_packages.ipynb) | Puts the answers together into **one travel package per region** (theme, best months, countries to sell, top places, hidden gems, **🍽️ typical food**) + a **7-day itinerary** for each package |

---

## 🔎 Main findings

- **Where:** Lisboa and the Algarve have half of all overnight stays. Only **6 of 308 municipalities** have 50% of them.
- **When:** **August** is the peak in every region. The Algarve is the most seasonal (52% of stays in June–September); Lisboa and Madeira are the most stable (39%).
- **Surprise:** municipalities **with a beach are not more seasonal** than the ones without (Mann-Whitney, p = 0.25).
- **Who:** the mix of countries depends on the region (Chi-square). The Irish prefer the Algarve, the Polish prefer Madeira, the Spanish prefer Centro and Alentejo.
- **What:** each region has a specialty (specialty index): Açores nature **6.0×**, Algarve beach **4.8×**, Centro historic villages **4.4×**, Madeira viewpoints **3.3×**. Lisboa, Norte and Alentejo are balanced, with a bit more culture.
- **Hidden gems:** 10 municipalities with many quality marks and few tourists, e.g. **Vila Nova de Foz Côa** (UNESCO rock art, only 13 000 stays a year).

## 🧳 The packages

One package per region: the theme is the region's specialty, and every other part comes from the 5 questions.

| Package | Best time to travel | When to sell | Sell in | Hidden gems to add |
|---|---|---|---|---|
| 🌲 Nature Escape · Azores | Apr, May, Jun | Jan, Feb, Mar | Canada, Switzerland, Austria | Santa Cruz das Flores |
| 🏖️ Beach & Sun · Algarve | May, Jun, Oct | Feb, Mar, Jul | Ireland, United Kingdom, Netherlands |  |
| 🏡 Historic Villages · Centre | May, Jun, Oct | Feb, Mar, Jul | Spain, Brazil, Poland | Mangualde, Montemor-o-Velho |
| 🔭 Island Views · Madeira | May, Jun, Oct | Feb, Mar, Jul | Poland, Denmark, Germany |  |
| 🏛️ Culture & Heritage · Alentejo | May, Jun, Oct | Feb, Mar, Jul | Spain, Belgium, Switzerland | Moura, Nisa, Borba, Alvito |
| 🏛️ Culture & Heritage · Lisbon | May, Jun, Sep | Feb, Mar, Jun | China, Brazil, United States |  |
| 🏛️ Culture & Heritage · North | May, Jun, Oct | Feb, Mar, Jul | Spain, Brazil, China | Vila Nova de Foz Côa, Marco de Canaveses, Torre de Moncorvo |

*Best time to travel = good months with fewer tourists (August is the peak for every package). When to sell = 3 months before (our assumption, see Limitations).*

Every package also says what **🍽️ you must try**: the traditional dishes of the region (7 Maravilhas da Gastronomia) and its DOP/IGP products, in English and **never repeated** in the same trip.

### 🗓️ Day-by-day itineraries

Each package has an itinerary, built with simple rules (code in [`app/itinerary.py`](app/itinerary.py), used by notebook 03 and by the app):

- **Islands:** the trip stays on **one island**.
- **Beach & Sun:** no jumping around: **one base town** and a different beach every day (less than 40 km, the closest first).
- **Other packages:** a road trip from the best town (UNESCO sites and historic villages count 3 times); each day the best town **less than 60 km** away. In the app the tourist can choose another start (e.g. Óbidos).
- **Hidden gems:** in trips of 5+ days, one day goes to the closest hidden gem.
- **Places per day** depend on the theme: 1 beach, 2 natural areas, 2 villages, 3 viewpoints, 4 monuments (completed with the towns around, less than 25 km).
- **Order:** the towns are put in the **shortest round trip** (back to the start at the end), so the trip never goes back and forth.
- The 7-day itineraries are saved in `data/clean/itineraries_7_days.csv`.

---

## 🧭 Run the app

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

The app has 3 tabs:
- **🧭 Plan my trip:** type of trip (beach, culture, villages, nature, viewpoints or **🎨 mix**) → *what to mix* (only for mix) → month → number of days → **click a region on the map** (or keep the region suggested by the data; e.g. culture in the Centre gives Óbidos, Alcobaça, Batalha, Tomar…). It shows the package, a **day-by-day itinerary** (on islands, the tourist chooses the island), when to go, how busy each town is (🟢 quiet · 🟡 normal · 🔴 busy) and a map.
- **📍 My Portugal:** the tourist adds the towns they've already visited (sidebar, or ✅ "I did this trip"). They appear as pins on a map, with the progress by region, and the itineraries **don't recommend them again**.
- **🌍 For travel agencies:** choose a country and see which packages to sell there (preference index).

*"I prefer fewer tourists"* skips the busiest half of the towns of the region in that month. Photos come from Wikipedia (they need internet).

## 🗂️ Project structure

```
Final Project/
├── app/
│   ├── app.py                  # Streamlit app "Plan my trip"
│   └── itinerary.py            # rules for the day-by-day itineraries
├── data/
│   ├── raw/                    # original files + SOURCES.md
│   └── clean/                  # files created by the notebooks
├── notebooks/
│   ├── 01_data_cleaning.ipynb
│   ├── 02_statistics.ipynb
│   └── 03_packages.ipynb
├── Discover_Portugal.twb       # Tableau workbook
├── requirements.txt
└── README.md
```

## ⚠️ Limitations

- Some INE values are **confidential** (hidden), so a few small municipalities have missing numbers.
- The municipality of places with only coordinates comes from the **nearest known place** (~93% right, KNN chosen after comparing 5 models).
- Each region has **one package**, with the theme of its specialty. Regions also have other things to offer (e.g. Óbidos, in Centro, has a beautiful lagoon *and* a medieval town).
- The itineraries skip classified places that don't interest most tourists (small churches, chapels, pillories, fountains, houses…). This list is a simple rule by type of place, not a popularity measure.
- The itineraries use **straight-line distances**, not real driving times, and don't include hotels or opening hours.
- Small classified monuments (road markers, pillories, stone crosses) **don't count** as quality markers: nobody travels to see them.
- **When to sell = 3 months before the trip** is our **assumption**: we have no data on when tourists book their holidays, and it can be different for each country.
- We only recommend **Blue Flag beaches** (official quality). Some wild and beautiful beaches, like **Praia de Cacela Velha**, don't have a Blue Flag, so they are not in the packages.

## 🔭 Future recommendations

- **Work with a local tourism professional.** Data alone can miss real treasures, like Cacela Velha. A tourism expert from Portugal can review the packages and add the places that the data doesn't show.
- Classify the beaches as **urban or natural**, so clients can choose the kind of beach they like (a more personal offer). The official source is the beach typology of the APA coastal programmes (*Programas da Orla Costeira*: Type I urban … Type IV natural), which is not yet available as one open table; a simple distance rule was tested but made too many mistakes.
- Add **wild beaches** from other sources (e.g. OpenStreetMap), with a clear label: "no Blue Flag".
- **Research when tourists book** their holidays (by country, e.g. Turismo de Portugal or travel agency surveys), to know exactly when to sell each package instead of our 3-month assumption.
- Build a **Food Route** 🍲. Portugal is famous for its excellent food and high-quality products (DOP/IGP cheeses, wines, olive oils…), so food should be a reason to travel, not only a tip. We tried a route from North to South (one stop per region, in the town with the most traditional restaurants), but it was too complex to do well in this project: restaurant data from OpenStreetMap is incomplete, and a good route needs restaurants, markets, wineries and festivals. Today each package only says what you **must try**.
- Add the **Registo Nacional de Turismo** (Turismo de Portugal): tourism activity companies (surf, hiking, boat trips…) and accommodation capacity. The open version on dados.gov.pt has not been updated since 2020, so a recent version is needed.
- **Take the model to other countries** (e.g. Spain or Italy). The method can be used again: preference index, specialty index, hidden gems and the itinerary rules. It only needs the overnight stays by month and by country of origin, and the places with a quality marker (UNESCO, Blue Flag, protected areas…) of that country.
- Add the **average price** of each destination (accommodation, food…), so clients can choose destinations that fit their **budget**. This also turns the packages into real offers.
