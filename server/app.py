from flask import Flask, Response, request, render_template_string
from SPARQLWrapper import SPARQLWrapper, JSON, TURTLE

app = Flask(__name__)

# -----------------------
# Configuration
# -----------------------
SPARQL_ENDPOINT = "http://localhost:3030/tolkien/sparql"
EX_NS = "https://example.org/resource/"

HIDDEN_PROPERTIES = {"label"}

DISPLAY_ORDER = [
    "type","name","gender","age","position","people","family","parentage",
    "siblings","spouse","children","location",
    "inverse_people","inverse_family","inverse_location"
]

# -----------------------
# Labels UI multilingues
# -----------------------
UI_LABELS = {
    "en": {"language":"Language","type":"RDF type","name":"Name","gender":"Gender","age":"Age",
           "position":"Position","people":"People","family":"Family","parentage":"Parents",
           "siblings":"Siblings","spouse":"Spouse","children":"Children","location":"Location",
           "inverse_people":"Characters","inverse_family":"Members",
           "inverse_location":"Related characters","graph_resources":"Graph resources"},
    "fr": {"language":"Langue","type":"Type RDF","name":"Nom","gender":"Genre","age":"Âge",
           "position":"Fonction","people":"Peuple","family":"Famille","parentage":"Parents",
           "siblings":"Fratrie","spouse":"Conjoint","children":"Enfants","location":"Lieu",
           "inverse_people":"Personnages","inverse_family":"Membres",
           "inverse_location":"Personnages associés","graph_resources":"Ressources du graphe"},
    "de": {"language":"Sprache","type":"RDF-Typ","name":"Name","gender":"Geschlecht","age":"Alter",
           "position":"Position","people":"Volk","family":"Familie","parentage":"Eltern",
           "siblings":"Geschwister","spouse":"Ehepartner","children":"Kinder","location":"Ort",
           "inverse_people":"Charaktere","inverse_family":"Mitglieder",
           "inverse_location":"Zugehörige Charaktere","graph_resources":"Graph-Ressourcen"},
    "es": {"language":"Idioma","type":"Tipo RDF","name":"Nombre","gender":"Género","age":"Edad",
           "position":"Posición","people":"Pueblo","family":"Familia","parentage":"Padres",
           "siblings":"Hermanos","spouse":"Cónyuge","children":"Hijos","location":"Lugar",
           "inverse_people":"Personajes","inverse_family":"Miembros",
           "inverse_location":"Personajes asociados","graph_resources":"Recursos del grafo"}
}

# -----------------------
# SPARQL utilitaire
# -----------------------
def sparql_query(query, return_format=JSON):
    sparql = SPARQLWrapper(SPARQL_ENDPOINT)
    sparql.setQuery(query)
    sparql.setReturnFormat(return_format)
    return sparql.query().convert()

def get_label(uri, lang):
    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?label WHERE {{
      {{
        <{uri}> rdfs:label ?label .
        FILTER(LANG(?label) = "{lang}")
      }}
      UNION
      {{
        <{uri}> rdfs:label ?label .
        FILTER(LANG(?label) = "en")
      }}
      UNION
      {{
        <{uri}> rdfs:label ?label .
        FILTER(LANG(?label) = "")
      }}
    }}
    LIMIT 1
    """
    res = sparql_query(query)

    if res["results"]["bindings"]:
        return res["results"]["bindings"][0]["label"]["value"]

    # fallback FINAL : nom URI
    return uri.split("/")[-1].replace("_", " ")


# -----------------------
# Page d’accueil
# -----------------------
@app.route("/")
def index():
    lang = request.args.get("lang", "en")
    ui = UI_LABELS.get(lang, UI_LABELS["en"])

    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT ?s WHERE {{
      ?s rdfs:label ?l .
      FILTER(STRSTARTS(STR(?s), "{EX_NS}"))
    }}
    """

    results = sparql_query(query)

    resources = []
    for row in results["results"]["bindings"]:
        uri = row["s"]["value"]
        label = get_label(uri, lang)
        resources.append((uri.split("/")[-1], label))

    resources.sort(key=lambda x: x[1])

    html = f"<h1>{ui['graph_resources']}</h1>"
    html += f"<p><b>{ui['language']} :</b> "
    html += f'<a href="?lang=en">EN</a> | <a href="?lang=fr">FR</a> | '
    html += f'<a href="?lang=de">DE</a> | <a href="?lang=es">ES</a></p><ul>'

    for name, label in resources:
        html += f'<li><a href="/resource/{name}?lang={lang}">{label}</a></li>'
    html += "</ul>"

    return render_template_string(html)

# -----------------------
# Fiche ressource
# -----------------------
@app.route("/resource/<name>")
def resource(name):
    lang = request.args.get("lang", "en")
    ui = UI_LABELS.get(lang, UI_LABELS["en"])
    uri = f"{EX_NS}{name}"

    if "text/turtle" in request.headers.get("Accept", ""):
        sparql = SPARQLWrapper(SPARQL_ENDPOINT)
        sparql.setQuery(f"DESCRIBE <{uri}>")
        sparql.setReturnFormat(TURTLE)
        return Response(sparql.query().convert(), mimetype="text/turtle")

    props = {}

    query_out = f"SELECT ?p ?o WHERE {{ <{uri}> ?p ?o }}"
    for r in sparql_query(query_out)["results"]["bindings"]:
        p = r["p"]["value"].split("/")[-1]
        if p in HIDDEN_PROPERTIES: continue
        props.setdefault(p, []).append(r["o"]["value"])

    query_in = f"SELECT ?s ?p WHERE {{ ?s ?p <{uri}> }}"
    for r in sparql_query(query_in)["results"]["bindings"]:
        p = "inverse_" + r["p"]["value"].split("/")[-1]
        props.setdefault(p, []).append(r["s"]["value"])

    title = get_label(uri, lang)
    html = f"<h1>{title}</h1>"
    html += f"<p>{ui['language']} : "
    html += f'<a href="?lang=en">EN</a> | <a href="?lang=fr">FR</a> | '
    html += f'<a href="?lang=de">DE</a> | <a href="?lang=es">ES</a></p>'

    html += "<table border='1' cellpadding='5'>"
    for key in DISPLAY_ORDER:
        if key not in props: continue
        values = []
        for v in props[key]:
            if v.startswith(EX_NS):
                label = get_label(v, lang)
                values.append(f'<a href="/resource/{v.split("/")[-1]}?lang={lang}">{label}</a>')
            else:
                values.append(v)
        html += f"<tr><th>{ui.get(key,key)}</th><td>{', '.join(values)}</td></tr>"
    html += "</table>"

    return render_template_string(html)

# -----------------------
# Lancement
# -----------------------
if __name__ == "__main__":
    app.run(debug=True)
