# Data sources

Where each file came from (link + download date). All files were downloaded on **2026-11-05**.

| File | What it has | Rows | Source |
|---|---|---|---|
| ine_overnight_stays_region_month.csv | Overnight stays by month (Jan 2023 – Aug 2026), by region down to municipality, by type of accommodation | 60 544 | INE – Statistics Portugal, indicator 0010735: https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_indicadores&indOcorrCod=0010735&contexto=bd&selTab=tab2 |
| ine_overnight_stays_nationality.csv | Overnight stays by year (2019, 2022–2025), by region down to municipality, by country of residence | 86 000 | INE – Statistics Portugal, indicator 0009183: https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_indicadores&indOcorrCod=0009183&contexto=bd&selTab=tab2 |
| blue_flag_2026.csv | Places with Blue Flag 2026 (beaches, marinas, eco-tourism boats): type, municipality, coordinates | 422 | ABAAE – Bandeira Azul, awarded 2026: https://bandeiraazul.abaae.pt/galardoados/galardoados-2026/ |
| protected_areas_portugal.csv | Protected areas (national park, natural parks, reserves, protected landscapes, natural monuments) with municipalities and coordinates | 304 | Wikidata (query.wikidata.org) |
| historic_and_schist_villages.csv | The 12 Aldeias Históricas and the 27 Aldeias do Xisto, with municipality | 39 | Wikipedia: https://pt.wikipedia.org/wiki/Aldeias_Hist%C3%B3ricas_de_Portugal and https://pt.wikipedia.org/wiki/Aldeias_do_Xisto (municipalities of the Aldeias Históricas added by hand) |
| heritage_monuments_portugal.csv | Classified heritage: Monumento Nacional, Interesse Público, UNESCO World Heritage; with municipality and coordinates | 4 140 | Wikidata (query.wikidata.org), property P1435 (heritage designation). Lisbon monuments got their municipality with a second query (located in Lisbon, Q597) |
| osm_places_portugal.csv | Museums, viewpoints and named beaches, with coordinates | 3 821 | OpenStreetMap, Overpass API: https://overpass-api.de |
| municipality_coordinates.csv | Coordinates of the 308 municipalities (for maps), with the DICO code | 308 | Wikidata (query.wikidata.org), items 'municipality of Portugal' (Q13217644), properties P625 and P6324 |
| dop_igp_products_portugal.csv | Food products with protected name (DOP and IGP) | 129 | Wikipedia: https://pt.wikipedia.org/wiki/Lista_de_produtos_com_denomina%C3%A7%C3%A3o_de_origem_protegida_de_Portugal and https://pt.wikipedia.org/wiki/Lista_de_produtos_com_indica%C3%A7%C3%A3o_geogr%C3%A1fica_protegida_de_Portugal |
| traditional_dishes_7_maravilhas_2011.csv | 70 traditional dishes of the contest 7 Maravilhas da Gastronomia (2011): category, region, result | 70 | Wikipedia: https://pt.wikipedia.org/wiki/Sete_maravilhas_da_gastronomia |
| municipality_boundaries_caop.geojson | Shapes (borders) of the 308 municipalities, with the DICO code, for the filled map in Tableau | 308 | Direção-Geral do Território, CAOP (Carta Administrativa Oficial de Portugal), GeoJSON version: https://github.com/nmota/caop_GeoJSON (file Portugal_Municipalities.geojson). Downloaded on 2026-11-10 |
| nuts2_regions_portugal.geojson | Shapes of the 7 regions (NUTS II), for the map of region specialties | 7 | Eurostat / GISCO, NUTS 2021 at 1:3 million, GeoJSON version: https://github.com/eurostat/Nuts2json (file pub/v2/2021/4326/03M/nutsrg_2.json, only Portugal). Downloaded on 2026-11-10 |

The INE files were downloaded with the INE JSON API:
`https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd=<indicator>&Dim1=<period>&lang=EN`

Data © OpenStreetMap contributors (ODbL). Wikidata is CC0.
