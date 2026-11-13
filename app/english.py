"""
English names for the places
----------------------------
Our data has the official Portuguese names (e.g. "Igreja de São Pedro").
The app is in English, so we translate the TYPE of place and keep the proper name:
    "Igreja de São Pedro"         -> "Church of São Pedro"
    "Centro Histórico do Porto"   -> "Historic Centre of Porto"
    "Praia da Marinha"            -> "Marinha Beach"
Town and village names stay in Portuguese.
"""

import re

# Some famous places: the official English name
FAMOUS = {
    "Mosteiro dos Jerónimos": "Jerónimos Monastery",
    "Mosteiro dos Jerónimos e Torre de Belém": "Jerónimos Monastery and Belém Tower",
    "Universidade de Coimbra - Alta e Sofia": "University of Coimbra",
    "Paisagem Cultural de Sintra": "Cultural Landscape of Sintra",
    "Paisagem da Cultura da Vinha da Ilha do Pico": "Vineyard Landscape of Pico Island",
    "Floresta Laurissilva na Madeira": "Laurisilva Forest of Madeira",
    "Cidade Fronteiriça e de Guarnição de Elvas e as suas Fortificações": "Garrison Border Town of Elvas and its Fortifications",
    "Centro Histórico de Guimarães e Zona de Couros": "Historic Centre of Guimarães",
    "Alto Douro Vinhateiro": "Alto Douro Wine Region",
    "Sítios de arte rupestre pré-histórica do Vale do Coa e de Siega Verde": "Prehistoric Rock Art of the Côa Valley",
    "Convento de Cristo": "Convent of Christ",
    "Palácio Nacional de Mafra e tapada": "National Palace of Mafra",
    "Torre de Belém": "Belém Tower",
    "Mosteiro da Batalha": "Batalha Monastery",
    "Mosteiro de Alcobaça": "Alcobaça Monastery",
    "Castelo de São Jorge": "São Jorge Castle",
    "Palácio Nacional da Pena": "Pena Palace",
}

# Type of place at the start of the name: Portuguese -> English (the longest first)
TYPES = [
    ("Núcleo urbano da vila", "Old town"),
    ("Centro Histórico", "Historic Centre"),
    ("Igreja Matriz", "Main Church"), ("Igreja Paroquial", "Parish Church"), ("Igreja", "Church"),
    ("Capela", "Chapel"), ("Ermida", "Hermitage"), ("Santuário", "Sanctuary"), ("Sé", "Cathedral"),
    ("Castelo", "Castle"), ("Mosteiro", "Monastery"), ("Convento", "Convent"),
    ("Palácio Nacional", "National Palace"), ("Palácio", "Palace"), ("Solar", "Manor house"),
    ("Casa", "House"), ("Quinta", "Estate"), ("Ponte", "Bridge"), ("Torre", "Tower"),
    ("Fortaleza", "Fortress"), ("Forte", "Fort"), ("Muralhas", "Walls"), ("Aqueduto", "Aqueduct"),
    ("Chafariz", "Fountain"), ("Pelourinho", "Pillory"), ("Cruzeiro", "Stone cross"),
    ("Museu Nacional", "National Museum"), ("Museu Municipal", "Municipal Museum"),
    ("Museu Etnográfico", "Ethnographic Museum"), ("Núcleo Museológico", "Museum"), ("Museu", "Museum"),
    ("Centro Interpretativo", "Interpretation Centre"), ("Centro de Interpretação", "Interpretation Centre"),
    ("Núcleo de arte rupestre", "Rock art site"), ("Estação arqueológica", "Archaeological site"),
    ("Anta", "Dolmen"), ("Castro", "Iron Age hillfort"), ("Miradouro", "Viewpoint"),
    ("Parque Natural", "Natural Park"), ("Parque Nacional", "National Park"),
    ("Parque Natural Marinho", "Marine Natural Park"), ("Reserva Natural", "Nature Reserve"),
    ("Zona de Paisagem Protegida", "Protected Landscape"), ("Paisagem Protegida", "Protected Landscape"),
    ("Paisagem Protegida Regional", "Protected Landscape"),
    ("Monumento Natural Regional", "Natural Monument"), ("Monumento Natural", "Natural Monument"),
    ("Mata Nacional", "National Forest"), ("Reserva Florestal Natural Parcial", "Forest Reserve"),
    ("Reserva Florestal", "Forest Reserve"), ("Gruta", "Cave"), ("Parque Mineiro", "Mining Park"),
    ("Cerca medieval", "Medieval walls"),
]
TYPES.sort(key=lambda pair: len(pair[0]), reverse=True)   # "Igreja Matriz" before "Igreja"

OF = r"(?:de|do|da|dos|das|d')"     # Portuguese words for "of" (with or without "the")


def english_name(name, category=None):
    """English version of a place name (the proper name stays in Portuguese)"""
    if not isinstance(name, str):
        return name
    if name not in FAMOUS:
        # Long official names: we keep only the main part ("Forte X (restos das muralhas)" -> "Forte X")
        name = re.split(r", | \(", name)[0].strip()
    if name in FAMOUS:
        return FAMOUS[name]

    # Beaches: "Praia da Marinha" -> "Marinha Beach", "Alemães" -> "Alemães Beach"
    if category == "beach":
        rest = re.sub(rf"(?i)^praia\s+{OF}?\s*", "", name).strip()
        return f"{rest} Beach"

    for portuguese, english in TYPES:
        match = re.match(rf"(?i)^{portuguese}\s+{OF}\s+(.*)$", name)      # "Igreja de São Pedro"
        if match:
            return f"{english} of {match.group(1)}"
        if name.lower() == portuguese.lower():                                 # just "Miradouro"
            return english
    return name     # other names stay as they are (e.g. "Igreja e Convento de São Francisco")


# ------------------------------------------------------------------
# Regions: the 7 tourism regions in English (the municipalities stay in Portuguese)
# ------------------------------------------------------------------
REGIONS = {"Açores": "Azores", "Centro": "Centre", "Norte": "North", "Lisboa": "Lisbon"}


def english_region(region):
    """ "Norte" -> "North" (Algarve, Alentejo and Madeira are the same in English)"""
    return REGIONS.get(region, region)


# ------------------------------------------------------------------
# Food: the traditional dishes and the local products (DOP / IGP) in English
# ------------------------------------------------------------------
DISHES = {
    "Alheira de Mirandela": "Mirandela alheira (smoked sausage)", "Bôla de Lamego": "Lamego meat bread",
    "Bolo do Caco": "Bolo do caco (Madeira flatbread)", "Espargos com ovos": "Wild asparagus with eggs",
    "Lapas da Madeira": "Madeira limpets", "Muxama de atum": "Dried tuna (muxama)",
    "Pastel de bacalhau": "Codfish cakes", "Pezinhos de Coentrada": "Pig's trotters with coriander",
    "Presunto de Barrancos": "Barrancos cured ham", "Queijo Serra da Estrela": "Serra da Estrela cheese",
    "Açorda à Alentejana": "Alentejo bread soup", "Caldo verde": "Caldo verde (kale soup)",
    "Caldo de cascas": "Bean pod soup", "Canja de Borrego": "Lamb broth",
    "Caspacho com carapaus fritos": "Gazpacho with fried mackerel", "Sopa da pedra": "Stone soup",
    "Sopa de cação": "Dogfish soup", "Sopa de castanhas": "Chestnut soup",
    "Sopa de peixe da Figueira": "Figueira fish soup", "Sopas do Espírito Santo": "Holy Spirit soup",
    "Açorda de bacalhau": "Codfish bread stew", "Açorda de sável": "Shad bread stew",
    "Arroz de lampreia": "Lamprey rice", "Arroz de Lingueirão": "Razor clam rice",
    "Bacalhau à Braz": "Bacalhau à Brás (cod with eggs and potatoes)",
    "Bacalhau à Gomes de Sá": "Bacalhau à Gomes de Sá (baked cod)",
    "Bacalhau à Zé do Pipo": "Bacalhau à Zé do Pipo (cod with mashed potatoes)",
    "Bife de atum à Madeirense": "Madeira tuna steak", "Polvo assado no forno": "Roasted octopus",
    "Sardinha assada": "Grilled sardines", "Amêijoas à Bulhão Pato": "Clams with garlic and coriander",
    "Arroz de marisco": "Seafood rice", "Camarão da Costa da Figueira": "Figueira shrimps",
    "Cavaco cozido com molho verde": "Slipper lobster with green sauce", "Cracas cozidas": "Boiled barnacles",
    "Lapas grelhadas dos Açores": "Grilled Azores limpets", "Mariscada de Sesimbra": "Sesimbra seafood platter",
    "Ostras do Sado": "Sado oysters", "Percebes de Aljezur": "Aljezur goose barnacles",
    "Xarém com conquilhas": "Corn porridge with clams (xarém)",
    "Alcatra da Ilha Terceira": "Terceira beef pot roast (alcatra)",
    "Alheira de Mirandela com grelos salteados": "Mirandela alheira with turnip greens",
    "Chanfana": "Chanfana (goat stewed in red wine)", "Cozido à portuguesa": "Portuguese stew (cozido)",
    "Cozido das Furnas": "Furnas volcanic stew", "Espetada de carne de vaca em espeto de pau de louro": "Beef skewers on bay laurel sticks",
    "Leitão da Bairrada": "Bairrada roast suckling pig", "Migas alentejanas": "Alentejo migas (bread and pork)",
    "Posta mirandesa": "Mirandesa beef steak", "Tripas à moda do Porto": "Porto-style tripe",
    "Arroz de pombo bravo com hortelã": "Wild pigeon rice with mint", "Coelho à Caçador": "Hunter's rabbit stew",
    "Coelho do Porto Santo à Caçador": "Porto Santo hunter's rabbit",
    "Empada de coelho bravo com arroz de pinhão e passas": "Wild rabbit pie",
    "Feijoada de javali": "Wild boar bean stew", "Javali no pote com castanhas": "Wild boar with chestnuts",
    "Perdiz à Algarvia": "Algarve-style partridge", "Perdiz à Caçador": "Hunter's partridge",
    "Perdiz de escabeche": "Partridge in escabeche", "Tordos fritos ou fritada dos passarinheiros": "Fried thrushes",
    "Ananás dos Açores": "Azores pineapple", "Bolo de mel": "Madeira honey cake",
    "Dom Rodrigo": "Dom Rodrigo (egg and almond sweet)", "Encharcada do Convento de Santa Clara": "Encharcada (convent egg sweet)",
    "Ovos moles de Aveiro": "Aveiro soft eggs (ovos moles)", "Pão de rala": "Pão de rala (almond convent cake)",
    "Pastel de Belém": "Pastel de Belém (custard tart)", "Pastéis de Tentúgal": "Tentúgal pastries",
    "Pudim Abade de Priscos": "Abade de Priscos pudding", "Sericaia ou Cericaia ou Sericá": "Sericaia (cinnamon egg pudding)",
}

# Products that don't follow the "type + place" rule below
PRODUCTS = {
    "Carnalentejana": "Alentejo beef", "Carne de Bovino Cruzado dos Lameiros do Barroso": "Barroso beef",
    "Carne de Bísaro Transmontano": "Trás-os-Montes Bísaro pork", "Queijo de Cabra Transmontano": "Trás-os-Montes goat cheese",
    "Cabrito Transmontano": "Trás-os-Montes kid goat", "Pêra Rocha do Oeste": "Rocha pears from the Oeste",
    "Ovos Moles de Aveiro": "Aveiro soft eggs (ovos moles)", "Fogaça da Feira": "Feira sweet bread (fogaça)",
    "Arroz Carolino das Lezírias Ribatejanas": "Ribatejo Carolino rice", "Travia da Beira Baixa": "Beira Baixa travia (fresh cheese)",
    "Requeijão da Beira Baixa": "Beira Baixa requeijão (fresh cheese)", "Requeijão da Serra da Estrela": "Serra da Estrela requeijão (fresh cheese)",
}

# Type of product at the start of the name: Portuguese -> English (the longest first)
PRODUCT_TYPES = [
    ("Azeitonas de conserva", "olives"), ("Azeitona de conserva", "olives"), ("Azeites", "olive oil"), ("Azeite", "olive oil"),
    ("Carne de Porco", "pork"), ("Carne", "beef"), ("Vitela", "veal"), ("Borrego", "lamb"), ("Cordeiro", "lamb"),
    ("Cabrito", "kid goat"), ("Presunto", "cured ham"), ("Ameixa", "plums"), ("Ananás", "pineapple"),
    ("Anona", "custard apple"), ("Cereja", "cherries"), ("Maçã", "apples"), ("Maracujá", "passion fruit"),
    ("Amêndoa", "almonds"), ("Castanha", "chestnuts"), ("Mel", "honey"), ("Queijos", "cheese"), ("Queijo", "cheese"),
    ("Sal", "salt"), ("Alheira", "alheira sausage"), ("Chouriça", "chouriço sausage"), ("Chouriço", "chouriço sausage"),
    ("Salpicão", "salpicão sausage"), ("Farinheira", "farinheira sausage"), ("Morcela", "blood sausage"),
    ("Paia", "paio sausage"), ("Paio", "paio sausage"), ("Painho", "paio sausage"), ("Linguíça", "linguiça sausage"),
    ("Linguiça", "linguiça sausage"), ("Lombo", "cured pork loin"), ("Cacholeira", "cacholeira sausage"),
    ("Sangueira", "sangueira sausage"), ("Butelo", "butelo sausage"), ("Batata doce", "sweet potatoes"),
    ("Batata", "potatoes"), ("Citrinos", "citrus fruit"), ("Pêssego", "peaches"), ("Meloa", "melons"),
    ("Pastel", "pastry"),
]
PRODUCT_TYPES.sort(key=lambda pair: len(pair[0]), reverse=True)
# Words that describe the product, not the place (e.g. "Chouriço de Carne de Estremoz" -> the place is Estremoz)
NOT_A_PLACE = r"^(?:Carne|Abóbora|Ossos|Pão|Azedo|Mouro|Doce|Branca|Branco|Enguitado|Toucinho|Lombo|Assar|Cozer|grosso|mestiço|Amarelo|Picante|Bravo)\b"


def english_food(name):
    """English name of a dish or a local product:
    "Sardinha assada" -> "Grilled sardines", "Mel da Serra de Monchique" -> "Monchique honey" """
    if not isinstance(name, str) or not name:
        return name
    name = re.sub(r"\s*\(.*\)", "", name).strip()                  # "Alheira de Mirandela (IG)" -> without "(IG)"
    if name in DISHES:
        return DISHES[name]
    # a product with several names: we keep the first ("Sal de Tavira ou Flor de Sal de Tavira" -> "Sal de Tavira")
    name = re.split(r"\s*/\s*| ou |, | e (?=[A-Z])", name)[0].strip()
    if name in PRODUCTS:
        return PRODUCTS[name]
    for portuguese, english in PRODUCT_TYPES:
        match = re.match(rf"(?i)^{portuguese}\s+(?:{OF}\s+|d´)?(.+)$", name)
        if match:
            place = match.group(1)
            if re.match(NOT_A_PLACE, place, re.I):                # "Carne de Estremoz" -> "Estremoz"
                place = re.split(rf"\s{OF}\s", place)[-1]
            place = re.sub(r"^(?:Serra|Terras Altas|Parque|Soutos) (?:de|da|do|das|dos) (?!Estrela)", "", place)
            place = place.replace(" - Açores", "")
            place = place.replace("Açores", "Azores").replace("S. Miguel", "São Miguel")
            return f"{place} {english}"
    return name


def english_foods(text):
    """The same for a list of foods in one text: "Caldo verde, Sardinha assada" """
    if not isinstance(text, str) or not text:
        return text
    return ", ".join(english_food(food) for food in text.split(", "))
