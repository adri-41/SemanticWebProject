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
    "type","name","gender","age","position","people","family","parentage","siblings",
    "spouse","children","location","inverse_people","inverse_family","inverse_location"
]

# -----------------------
# Labels UI multilingues
# -----------------------
UI_LABELS = {
    "en": {"language":"Language","type":"RDF type","name":"Name","gender":"Gender","age":"Age",
           "position":"Position","people":"People","family":"Family","parentage":"Parents",
           "siblings":"Siblings","spouse":"Spouse","children":"Children","location":"Location",
           "inverse_people":"Characters","inverse_family":"Members","inverse_location":"Related characters",
           "graph_resources":"Graph Resources"},
    "fr": {"language":"Langue","type":"Type RDF","name":"Nom","gender":"Genre","age":"Âge",
           "position":"Fonction","people":"Peuple","family":"Famille","parentage":"Parents",
           "siblings":"Fratrie","spouse":"Conjoint","children":"Enfants","location":"Lieu",
           "inverse_people":"Personnages","inverse_family":"Membres","inverse_location":"Personnages associés",
           "graph_resources":"Ressources du graphe"},
    "de": {"language":"Sprache","type":"RDF-Typ","name":"Name","gender":"Geschlecht","age":"Alter",
           "position":"Position","people":"Volk","family":"Familie","parentage":"Eltern",
           "siblings":"Geschwister","spouse":"Ehepartner","children":"Kinder","location":"Ort",
           "inverse_people":"Charaktere","inverse_family":"Mitglieder","inverse_location":"Zugehörige Charaktere",
           "graph_resources":"Graph-Ressourcen"},
    "es": {"language":"Idioma","type":"Tipo RDF","name":"Nombre","gender":"Género","age":"Edad",
           "position":"Posición","people":"Pueblo","family":"Familia","parentage":"Padres",
           "siblings":"Hermanos","spouse":"Cónyuge","children":"Hijos","location":"Lugar",
           "inverse_people":"Personajes","inverse_family":"Miembros","inverse_location":"Personajes asociados",
           "graph_resources":"Recursos del grafo"}
}

# -----------------------
# Traductions ressources
# -----------------------
TRANSLATIONS = {
    "aragorn_ii": {"en":"Aragorn II","fr":"Aragorn II","de":"Aragorn II","es":"Aragorn II"},
    "arantar": {"en":"Arantar","fr":"Arantar","de":"Arantar","es":"Arantar"},
    "aranuir": {"en":"Aranuir","fr":"Aranuir","de":"Aranuir","es":"Aranuir"},
}

# -----------------------
# Utilitaire SPARQL
# -----------------------
def sparql_query(query, return_format=JSON):
    sparql = SPARQLWrapper(SPARQL_ENDPOINT)
    sparql.setQuery(query)
    sparql.setReturnFormat(return_format)
    return sparql.query().convert()

# -----------------------
# Label multilingue
# -----------------------
def get_label(uri, lang="en"):
    name = uri.split("/")[-1]
    if name in TRANSLATIONS:
        return TRANSLATIONS[name].get(lang, name)
    return name.replace("_", " ")

# -----------------------
# Page d’accueil
# -----------------------
@app.route("/")
def index():
    lang = request.args.get("lang","en")
    ui = UI_LABELS.get(lang, UI_LABELS["en"])

    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?s WHERE {{
      ?s rdfs:label ?label .
      FILTER(STRSTARTS(STR(?s), "{EX_NS}"))
    }}
    ORDER BY ?s
    """

    results = sparql_query(query)

    html = f"<h1>{ui['graph_resources']}</h1>"
    html += f"<p><b>{ui['language']} :</b> "
    html += f'<a href="?lang=en">EN</a> | <a href="?lang=fr">FR</a> | <a href="?lang=de">DE</a> | <a href="?lang=es">ES</a></p>'
    html += "<ul>"

    for row in results["results"]["bindings"]:
        uri = row["s"]["value"]
        name = uri.split("/")[-1]
        html += f'<li><a href="/resource/{name}?lang={lang}">{get_label(uri, lang)}</a></li>'

    html += "</ul>"
    return render_template_string(html)

# -----------------------
# Fiche ressource
# -----------------------
@app.route("/resource/<name>")
def resource(name):
    lang = request.args.get("lang","en")
    ui = UI_LABELS.get(lang, UI_LABELS["en"])
    uri = f"<{EX_NS}{name}>"

    if "text/turtle" in request.headers.get("Accept",""):
        sparql = SPARQLWrapper(SPARQL_ENDPOINT)
        sparql.setQuery(f"DESCRIBE {uri}")
        sparql.setReturnFormat(TURTLE)
        return Response(sparql.query().convert(), mimetype="text/turtle")

    props = {}

    query_out = f"SELECT ?p ?o WHERE {{ {uri} ?p ?o }}"
    for row in sparql_query(query_out)["results"]["bindings"]:
        p = row["p"]["value"].split("/")[-1]
        if p in HIDDEN_PROPERTIES: continue
        props.setdefault(p, []).append(row["o"]["value"])

    query_in = f"SELECT ?s ?p WHERE {{ ?s ?p {uri} }}"
    for row in sparql_query(query_in)["results"]["bindings"]:
        key = "inverse_" + row["p"]["value"].split("/")[-1]
        props.setdefault(key, []).append(row["s"]["value"])

    html = f"<h1>{get_label(EX_NS + name, lang)}</h1>"
    html += f"<p>{ui['language']} : <a href='?lang=en'>EN</a> | <a href='?lang=fr'>FR</a> | <a href='?lang=de'>DE</a> | <a href='?lang=es'>ES</a></p>"
    html += "<table border='1' cellpadding='5'>"

    for key in DISPLAY_ORDER:
        if key not in props: continue
        values=[]
        for v in props[key]:
            if v.startswith(EX_NS):
                target=v.split("/")[-1]
                values.append(f'<a href="/resource/{target}?lang={lang}">{get_label(v,lang)}</a>')
            else:
                values.append(v)
        html += f"<tr><th>{ui.get(key,key)}</th><td>{', '.join(values)}</td></tr>"

    html += "</table>"
    html += f"""
    <p><b>RDF :</b> <a href="/resource/{name}" onclick="fetchTurtle(event)">Voir Turtle</a></p>
    <script>
    function fetchTurtle(e){{
        e.preventDefault();
        fetch(window.location.href,{{headers:{{'Accept':'text/turtle'}}}})
        .then(r=>r.text())
        .then(t=>{{const w=window.open();w.document.write('<pre>'+t+'</pre>');}});
    }}
    </script>
    """
    return render_template_string(html)

if __name__ == "__main__":
    app.run(debug=True)
