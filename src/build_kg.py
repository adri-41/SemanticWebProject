import os
import re
import time
import mwclient
import mwparserfromhell
from rdflib import Graph, Namespace, RDF, RDFS, Literal, URIRef

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
EX = Namespace("https://example.org/resource/")
g.bind("ex", EX)
g.bind("rdfs", RDFS)

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
        content = match.group(1)
        return content.split("|")[-1]
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
    """Nettoie une valeur pour une URI valide"""
    name = clean_wikilinks(name)
    name = re.sub(r"[^\w\s-]", "", name)
    return name.strip().replace(" ", "_")

def name_to_uri(name):
    return EX[normalize_name(name)]

def page_exists(site, title):
    try:
        return site.pages[title].exists
    except:
        return False

# Propriétés relationnelles
LINK_PROPERTIES = {
    "children",
    "parentage",
    "family",
    "location",
    "siblings",
    "spouse",
    "people"
}

# Typage des entités liées
ENTITY_TYPES = {
    "people": EX.People,
    "location": EX.Place,
    "family": EX.Family,
    "children": EX.Character,
    "parentage": EX.Character,
    "siblings": EX.Character,
    "spouse": EX.Character
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

    g.add((char_uri, RDF.type, EX.Character))
    g.add((
        char_uri,
        RDFS.label,
        Literal(infobox.get("name", page.name), lang="en")
    ))

    for key, value in infobox.items():
        cleaned = clean_value(value)
        if not cleaned:
            continue

        prop_uri = EX[key.replace(" ", "_")]
        values = cleaned if isinstance(cleaned, list) else [cleaned]

        for v in values:
            if key in LINK_PROPERTIES and page_exists(site, v):
                target_uri = name_to_uri(v)

                g.add((char_uri, prop_uri, target_uri))

                # 🔹 créer la ressource liée si absente
                if (target_uri, RDF.type, None) not in g:
                    rdf_type = ENTITY_TYPES.get(key, EX.Resource)
                    g.add((target_uri, RDF.type, rdf_type))
                    g.add((target_uri, RDFS.label, Literal(v)))

                # 🔹 relations inverses
                if key == "children":
                    g.add((target_uri, EX.hasParent, char_uri))
                elif key == "parentage":
                    g.add((target_uri, EX.hasChild, char_uri))
                elif key == "spouse":
                    g.add((target_uri, EX.hasSpouse, char_uri))

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

print("✅ kg.ttl généré avec entités liées propres !")
