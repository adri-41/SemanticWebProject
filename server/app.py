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
    "type",
    "name",
    "gender",
    "age",
    "position",
    "people",
    "family",
    "parentage",
    "siblings",
    "spouse",
    "children",
    "location",
    "inverse_people",
    "inverse_family",
    "inverse_location"
]

LABELS = {
    "type": "Type RDF",
    "name": "Nom",
    "gender": "Genre",
    "age": "Âge",
    "position": "Fonction",
    "people": "Peuple",
    "family": "Famille",
    "parentage": "Parents",
    "siblings": "Fratrie",
    "spouse": "Conjoint",
    "children": "Enfants",
    "location": "Lieu",
    "inverse_people": "Personnages",
    "inverse_family": "Membres",
    "inverse_location": "Personnages associés"
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
# Page d’accueil
# -----------------------
@app.route("/")
def index():
    query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?s ?label WHERE {
      ?s rdfs:label ?label .
      FILTER(STRSTARTS(STR(?s), "https://example.org/resource/"))
    }
    ORDER BY ?label
    """

    results = sparql_query(query)

    html = "<h1>Ressources du graphe</h1><ul>"
    for row in results["results"]["bindings"]:
        uri = row["s"]["value"]
        label = row["label"]["value"]
        name = uri.split("/")[-1]
        html += f'<li><a href="/resource/{name}">{label}</a></li>'
    html += "</ul>"

    return render_template_string(html)

# -----------------------
# Fiche ressource Linked Data
# -----------------------
@app.route("/resource/<name>")
def resource(name):
    uri = f"<{EX_NS}{name}>"

    # -------- Turtle (DESCRIBE) --------
    if "text/turtle" in request.headers.get("Accept", ""):
        sparql = SPARQLWrapper(SPARQL_ENDPOINT)
        sparql.setQuery(f"DESCRIBE {uri}")
        sparql.setReturnFormat(TURTLE)
        turtle = sparql.query().convert()
        return Response(turtle, mimetype="text/turtle")

    props = {}

    # -------- Propriétés sortantes --------
    query_out = f"""
    SELECT ?p ?o WHERE {{
      {uri} ?p ?o .
    }}
    """

    results = sparql_query(query_out)

    for row in results["results"]["bindings"]:
        p = row["p"]["value"].split("/")[-1]
        o = row["o"]["value"]

        if p in HIDDEN_PROPERTIES:
            continue

        props.setdefault(p, []).append(o)

    # -------- Propriétés entrantes --------
    query_in = f"""
    SELECT ?s ?p WHERE {{
      ?s ?p {uri} .
    }}
    """

    results = sparql_query(query_in)

    for row in results["results"]["bindings"]:
        p = "inverse_" + row["p"]["value"].split("/")[-1]
        s = row["s"]["value"]
        props.setdefault(p, []).append(s)

    # -------- HTML --------
    html = f"<h1>{name.replace('_', ' ')}</h1>"
    html += "<table border='1' cellpadding='5'>"

    for key in DISPLAY_ORDER:
        if key not in props:
            continue

        values = []
        for v in props[key]:
            if v.startswith(EX_NS):
                target = v.split("/")[-1]
                values.append(
                    f'<a href="/resource/{target}">{target.replace("_", " ")}</a>'
                )
            else:
                values.append(v)

        label = LABELS.get(key, key)
        html += f"""
        <tr>
            <th>{label}</th>
            <td>{", ".join(values)}</td>
        </tr>
        """

    html += "</table>"

    html += f"""
    <p><b>RDF :</b>
    <a href="/resource/{name}" onclick="fetchTurtle(event)">
        Voir Turtle
    </a></p>

    <script>
    function fetchTurtle(e) {{
        e.preventDefault();
        fetch(window.location.href, {{
            headers: {{'Accept': 'text/turtle'}}
        }})
        .then(r => r.text())
        .then(t => {{
            const w = window.open();
            w.document.write('<pre>' + t + '</pre>');
        }});
    }}
    </script>
    """

    return render_template_string(html)

# -----------------------
# Lancement
# -----------------------
if __name__ == "__main__":
    app.run(debug=True)