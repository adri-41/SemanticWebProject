from flask import Flask, Response, request, render_template_string
from rdflib import Graph, URIRef, RDFS, RDF

app = Flask(__name__)

# Chargement du KG
g = Graph()
g.parse("../data/kg.ttl", format="turtle")

EX_NS = "https://example.org/resource/"

# Propriétés à cacher
HIDDEN_PROPERTIES = {
    "label"
}

# Ordre d’affichage
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

# Labels lisibles
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
# Page d’accueil
# -----------------------
@app.route("/")
def index():
    characters = []
    for s in g.subjects(RDFS.label, None):
        if str(s).startswith(EX_NS):
            label = g.value(subject=s, predicate=RDFS.label)
            characters.append((s.split("/")[-1], str(label)))

    html = "<h1>Ressources du graphe</h1><ul>"
    for name, label in sorted(characters):
        html += f'<li><a href="/resource/{name}">{label}</a></li>'
    html += "</ul>"

    return render_template_string(html)

# -----------------------
# Fiche ressource
# -----------------------
@app.route("/resource/<name>")
def resource(name):
    uri = URIRef(EX_NS + name)

    g_person = Graph()

    # Triplets sortants
    for s, p, o in g.triples((uri, None, None)):
        g_person.add((s, p, o))

    # Content negotiation : Turtle
    if "text/turtle" in request.headers.get("Accept", ""):
        turtle = g_person.serialize(format="turtle")
        return Response(turtle, mimetype="text/turtle")

    props = {}

    # Propriétés sortantes
    for s, p, o in g_person:
        key = str(p).split("/")[-1]
        if key in HIDDEN_PROPERTIES:
            continue
        props.setdefault(key, []).append(o)

    # 🔹 Relations entrantes (clé pour éviter les pages vides)
    for s, p, o in g.triples((None, None, uri)):
        key = f"inverse_{str(p).split('/')[-1]}"
        props.setdefault(key, []).append(s)

    # HTML
    html = f"<h1>{name.replace('_', ' ')}</h1>"
    html += "<table border='1' cellpadding='5'>"

    for key in DISPLAY_ORDER:
        if key not in props:
            continue

        values = []
        for o in props[key]:
            if isinstance(o, URIRef) and str(o).startswith(EX_NS):
                target = str(o).split("/")[-1]
                values.append(
                    f'<a href="/resource/{target}">{target.replace("_", " ")}</a>'
                )
            else:
                values.append(str(o))

        label = LABELS.get(key, key)
        html += f"""
        <tr>
            <th>{label}</th>
            <td>{", ".join(values)}</td>
        </tr>
        """

    html += "</table>"

    # Lien Turtle
    html += f"""
    <p><b>RDF :</b>
    <a href="/resource/{name}" onclick="fetchTurtle(event)">
        Télécharger Turtle
    </a>
    </p>

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

if __name__ == "__main__":
    app.run(debug=True)
