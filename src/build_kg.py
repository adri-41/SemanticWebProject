import os
import re
import time
import mwclient
import mwparserfromhell
from rdflib import Graph, Namespace, RDF, RDFS, Literal, URIRef
from rdflib.namespace import OWL

# -----------------------
# Connexion Tolkien Gateway
# -----------------------
site = mwclient.Site(
    'tolkiengateway.net',
    path='/w/',
    clients_useragent='SemanticWebProject/1.0'
)

# -----------------------
# Graphe RDF
# -----------------------
g = Graph()

EX  = Namespace("https://example.org/resource/")
DBO = Namespace("http://dbpedia.org/ontology/")
DBR = Namespace("http://dbpedia.org/resource/")

g.bind("ex", EX)
g.bind("dbo", DBO)
g.bind("dbr", DBR)
g.bind("rdfs", RDFS)
g.bind("owl", OWL)

# -----------------------
# Nettoyage du wikitext
# -----------------------
def extract_infobox(wikitext, template_name="Infobox character"):
    wikicode = mwparserfromhell.parse(wikitext)
    for tpl in wikicode.filter_templates():
        if tpl.name.matches(template_name):
            return {
                param.name.strip(): str(param.value).strip()
                for param in tpl.params
            }
    return {}

def remove_refs(text):
    return re.sub(r"<ref[^>]*>.*?</ref>", "", text)

def clean_wikilinks(text):
    def repl(match):
        return match.group(1).split("|")[-1]
    return re.sub(r"\[\[(.*?)\]\]", repl, text)

def clean_dates(text):
    return re.sub(r"\{\{SR\|(\d+)\}\}", r"\1", text)

def split_list(text):
    text = text.replace(" and ", ",")
    return [t.strip() for t in text.split(",") if t.strip()]

def clean_value(value):
    if not value:
        return None
    value = remove_refs(value)
    value = clean_dates(value)
    value = clean_wikilinks(value)
    value = value.strip()
    if "," in value:
        return split_list(value)
    return value

# -----------------------
# Utilitaires RDF
# -----------------------
def normalize_name(name):
    name = clean_wikilinks(name)
    name = re.sub(r"[^\w\s-]", "", name)
    return name.strip().replace(" ", "_")

def name_to_uri(name):
    return EX[normalize_name(name)]

def dbpedia_uri(name):
    return DBR[normalize_name(name)]

def page_exists(site, title):
    try:
        return site.pages[title].exists
    except:
        return False

# -----------------------
# Mapping vers DBpedia
# -----------------------
PROPERTY_MAPPING = {
    "family":   DBO.family,
    "location": DBO.location,
    "spouse":   DBO.spouse,
    "people":   DBO.ethnicGroup,
    "children": DBO.child,
    "parentage": DBO.parent
}

LINK_PROPERTIES = set(PROPERTY_MAPPING.keys())

ENTITY_TYPES = {
    "people":   DBO.EthnicGroup,
    "location": DBO.Place,
    "family":   DBO.Family,
    "children": DBO.FictionalCharacter,
    "parentage": DBO.FictionalCharacter,
    "siblings": DBO.FictionalCharacter,
    "spouse":   DBO.FictionalCharacter
}

# -----------------------
# Construction du KG
# -----------------------
category = site.categories["Third Age characters"]

for page in category:
    text = page.text()
    infobox = extract_infobox(text)
    if not infobox:
        continue

    char_uri = name_to_uri(page.name)

    # Type DBpedia
    g.add((char_uri, RDF.type, DBO.FictionalCharacter))

    # Label
    g.add((
        char_uri,
        RDFS.label,
        Literal(infobox.get("name", page.name), lang="en")
    ))

    # Alignement DBpedia
    g.add((
        char_uri,
        OWL.sameAs,
        dbpedia_uri(page.name)
    ))

    for key, value in infobox.items():
        cleaned = clean_value(value)
        if not cleaned:
            continue

        prop_uri = PROPERTY_MAPPING.get(key, EX[key.replace(" ", "_")])
        values = cleaned if isinstance(cleaned, list) else [cleaned]

        for v in values:
            if key in LINK_PROPERTIES and page_exists(site, v):
                target_uri = name_to_uri(v)

                g.add((char_uri, prop_uri, target_uri))

                if (target_uri, RDF.type, None) not in g:
                    g.add((target_uri, RDF.type, ENTITY_TYPES.get(key, EX.Resource)))
                    g.add((target_uri, RDFS.label, Literal(v, lang="en")))
                    g.add((target_uri, OWL.sameAs, dbpedia_uri(v)))

            else:
                g.add((char_uri, prop_uri, Literal(v)))

    time.sleep(1)

# -----------------------
# Sauvegarde
# -----------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

g.serialize(os.path.join(DATA_DIR, "kg.ttl"), format="turtle")

print("✅ kg.ttl généré avec alignement DBpedia propre")