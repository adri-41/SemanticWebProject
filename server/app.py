from flask import Flask, Response, request, render_template_string
from rdflib import Graph, URIRef, RDFS, RDF

app = Flask(__name__)

# Chargement du KG
g = Graph()
g.parse("../data/kg.ttl", format="turtle")

EX_NS = "https://example.org/resource/"

# Propriétés à cacher
HIDDEN_PROPERTIES = {"label"}

# Ordre d’affichage
DISPLAY_ORDER = [
    "type","name","gender","age","position","people","family","parentage","siblings",
    "spouse","children","location","inverse_people","inverse_family","inverse_location"
]

# Labels multilingues UI
UI_LABELS = {
    "en": {"language":"Language","type":"RDF type","name":"Name","gender":"Gender","age":"Age","position":"Position","people":"People","family":"Family","parentage":"Parents","siblings":"Siblings","spouse":"Spouse","children":"Children","location":"Location","inverse_people":"Characters","inverse_family":"Members","inverse_location":"Related characters","graph_resources":"Graph Resources"},
    "fr": {"language":"Langue","type":"Type RDF","name":"Nom","gender":"Genre","age":"Âge","position":"Fonction","people":"Peuple","family":"Famille","parentage":"Parents","siblings":"Fratrie","spouse":"Conjoint","children":"Enfants","location":"Lieu","inverse_people":"Personnages","inverse_family":"Membres","inverse_location":"Personnages associés","graph_resources":"Ressources du graphe"},
    "de": {"language":"Sprache","type":"RDF-Typ","name":"Name","gender":"Geschlecht","age":"Alter","position":"Position","people":"Volk","family":"Familie","parentage":"Eltern","siblings":"Geschwister","spouse":"Ehepartner","children":"Kinder","location":"Ort","inverse_people":"Charaktere","inverse_family":"Mitglieder","inverse_location":"Zugehörige Charaktere","graph_resources":"Graph-Ressourcen"},
    "es": {"language":"Idioma","type":"Tipo RDF","name":"Nombre","gender":"Género","age":"Edad","position":"Posición","people":"Pueblo","family":"Familia","parentage":"Padres","siblings":"Hermanos","spouse":"Cónyuge","children":"Hijos","location":"Lugar","inverse_people":"Personajes","inverse_family":"Miembros","inverse_location":"Personajes asociados","graph_resources":"Recursos del grafo"}
}

# -----------------------
# Traductions des ressources
# -----------------------
TRANSLATIONS = {
    "aragorn_ii": {"en":"Aragorn II","fr":"Aragorn II","de":"Aragorn II","es":"Aragorn II"},
    "arantar": {"en":"Arantar","fr":"Arantar","de":"Arantar","es":"Arantar"},
    "aranuir": {"en":"Aranuir","fr":"Aranuir","de":"Aranuir","es":"Aranuir"},
    "araphant": {"en":"Araphant","fr":"Araphant","de":"Araphant","es":"Araphant"},
    "araphor": {"en":"Araphor","fr":"Araphor","de":"Araphor","es":"Araphor"},
    "arassuil": {"en":"Arassuil","fr":"Arassuil","de":"Arassuil","es":"Arassuil"},
    "araval": {"en":"Araval","fr":"Araval","de":"Araval","es":"Araval"},
    # ajoute ici tous les personnages de ton KG...
}

# -----------------------
# Utilitaire multilingue
# -----------------------
def get_label(graph, uri, lang="en"):
    name = str(uri).split("/")[-1]
    if name in TRANSLATIONS:
        return TRANSLATIONS[name].get(lang, name)
    # fallback KG
    for label in graph.objects(uri, RDFS.label):
        if label.language == lang:
            return str(label)
    for label in graph.objects(uri, RDFS.label):
        if label.language == "en":
            return str(label)
    for label in graph.objects(uri, RDFS.label):
        if label.language is None:
            return str(label)
    return name.replace("_"," ")

# -----------------------
# Page d’accueil
# -----------------------
@app.route("/")
def index():
    lang = request.args.get("lang","en")
    ui = UI_LABELS.get(lang, UI_LABELS["en"])

    characters = set()
    for s in g.subjects(RDFS.label, None):
        if str(s).startswith(EX_NS):
            characters.add(s)

    # Convertir en liste triée avec labels
    characters_list = []
    for s in sorted(characters, key=lambda x: get_label(g, x, lang)):
        label = get_label(g, s, lang)
        characters_list.append((s.split("/")[-1], label))

    html = f"<h1>{ui['graph_resources']}</h1>"
    html += f"<p><b>{ui['language']} :</b> "
    html += f'<a href="?lang=en">EN</a> | <a href="?lang=fr">FR</a> | <a href="?lang=de">DE</a> | <a href="?lang=es">ES</a></p>'
    html += "<ul>"
    for name, label in characters_list:  # <- utilisation correcte
        html += f'<li><a href="/resource/{name}?lang={lang}">{label}</a></li>'
    html += "</ul>"
    return render_template_string(html)

# -----------------------
# Fiche ressource
# -----------------------
@app.route("/resource/<name>")
def resource(name):
    lang = request.args.get("lang","en")
    ui = UI_LABELS.get(lang, UI_LABELS["en"])
    uri = URIRef(EX_NS + name)

    g_person = Graph()
    for s,p,o in g.triples((uri,None,None)):
        g_person.add((s,p,o))

    if "text/turtle" in request.headers.get("Accept",""):
        return Response(g_person.serialize(format="turtle"),mimetype="text/turtle")

    props = {}
    for s,p,o in g_person:
        key = str(p).split("/")[-1]
        if key in HIDDEN_PROPERTIES: continue
        props.setdefault(key,[]).append(o)
    for s,p,o in g.triples((None,None,uri)):
        key = f"inverse_{str(p).split('/')[-1]}"
        props.setdefault(key,[]).append(s)

    title = get_label(g, uri, lang)
    html = f"<h1>{title}</h1>"
    html += f"<p>{ui['language']} : <a href='/resource/{name}?lang=en'>EN</a> | <a href='/resource/{name}?lang=fr'>FR</a> | <a href='/resource/{name}?lang=de'>DE</a> | <a href='/resource/{name}?lang=es'>ES</a></p>"
    html += "<table border='1' cellpadding='5'>"

    for key in DISPLAY_ORDER:
        if key not in props: continue
        values=[]
        for o in props[key]:
            if isinstance(o, URIRef) and str(o).startswith(EX_NS):
                target = str(o).split("/")[-1]
                label = get_label(g, o, lang)
                values.append(f'<a href="/resource/{target}?lang={lang}">{label}</a>')
            else:
                values.append(str(o))
        label = ui.get(key,key)
        html += f"<tr><th>{label}</th><td>{', '.join(values)}</td></tr>"

    html += f"""
    </table>
    <p><b>RDF :</b>
    <a href="/resource/{name}" onclick="fetchTurtle(event)">{ui['type']}</a>
    </p>
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

if __name__=="__main__":
    app.run(debug=True)
