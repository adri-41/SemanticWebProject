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
EX = Namespace("https://example.org/resource/")
DBO = Namespace("http://dbpedia.org/ontology/")

g.bind("ex", EX)
g.bind("dbo", DBO)
g.bind("rdfs", RDFS)
g.bind("owl", OWL)

# -----------------------
# Nettoyage du wikitext
# -----------------------
def extract_infobox(wikitext):
    wikicode = mwparserfromhell.parse(wikitext)

    print("\nTEMPLATES TROUVÉS DANS LA PAGE :")
    for tpl in wikicode.filter_templates():
        print("  -", repr(str(tpl.name)))

    for tpl in wikicode.filter_templates():
        tpl_name = tpl.name.strip().lower()
        if "infobox" in tpl_name:
            print("INFOBOX DÉTECTÉE :", repr(str(tpl.name)))
            infobox = {
                param.name.strip(): str(param.value).strip()
                for param in tpl.params
            }
            print("CONTENU INFOBOX BRUT :", infobox)
            return infobox

    print("AUCUNE INFOBOX DÉTECTÉE")
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
    "children", "parentage", "family", "location", "siblings", "spouse", "people"
}

PROPERTY_MAPPING = {
    "family": DBO.family,
    "location": DBO.location,
    "spouse": DBO.spouse,
    "people": DBO.ethnicGroup
}

ENTITY_TYPES = {
    "people": DBO.EthnicGroup,
    "location": DBO.Place,
    "family": DBO.Family,
    "children": DBO.FictionalCharacter,
    "parentage": DBO.FictionalCharacter,
    "siblings": DBO.FictionalCharacter,
    "spouse": DBO.FictionalCharacter
}

# -----------------------
# Construction du KG
# -----------------------
category = site.categories["Third Age characters"]
MAX_PAGES = 50

for i, page in enumerate(category):
    if i >= MAX_PAGES:
        break

    print("\n" + "=" * 70)
    print(f"PAGE : {page.name}")

    try:
        text = page.text()
    except Exception as e:
        print(f"ERREUR RÉCUPÉRATION PAGE : {e}")
        time.sleep(5)
        continue

    infobox = extract_infobox(text)

    if not infobox:
        print(f"INFOBOX VIDE POUR {page.name}")

    # Création entité
    char_uri = name_to_uri(page.name)
    print("URI PERSONNAGE :", char_uri)

    g.add((char_uri, RDF.type, DBO.FictionalCharacter))
    g.add((char_uri, RDFS.label, Literal(page.name, lang="en")))

    dbpedia_uri = URIRef("http://dbpedia.org/resource/" + normalize_name(page.name))
    g.add((char_uri, OWL.sameAs, dbpedia_uri))

    if infobox:
        for key, value in infobox.items():
            print(f"\nCLÉ INFOBOX : {repr(key)}")
            print(f"  VALEUR BRUTE : {repr(value)}")

            cleaned = clean_value(value)
            print(f"  VALEUR NETTOYÉE : {repr(cleaned)}")

            if not cleaned:
                print("   IGNORÉE (vide après nettoyage)")
                continue

            prop_uri = PROPERTY_MAPPING.get(key, EX[key.replace(" ", "_")])
            values = cleaned if isinstance(cleaned, list) else [cleaned]

            for v in values:
                if key in LINK_PROPERTIES:
                    target_uri = name_to_uri(v)
                    g.add((char_uri, prop_uri, target_uri))

                    if (target_uri, RDF.type, None) not in g:
                        rdf_type = ENTITY_TYPES.get(key, EX.Resource)
                        g.add((target_uri, RDF.type, rdf_type))
                        g.add((target_uri, RDFS.label, Literal(v)))
                else:
                    g.add((char_uri, prop_uri, Literal(v)))

    print(f"FIN PAGE {page.name} — Triples actuels : {len(g)}")
    time.sleep(3)

# -----------------------
# Sauvegarde
# -----------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

g.serialize(os.path.join(DATA_DIR, "kg.ttl"), format="turtle")
print("\nkg.ttl généré avec DEBUG COMPLET")
