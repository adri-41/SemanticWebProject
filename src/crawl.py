import mwclient

site = mwclient.Site('tolkiengateway.net', path='/w/', clients_useragent='SemanticWebProject/1.0')

# Exemple : récupérer Elrond
page = site.pages['Elrond']
text = page.text()
print(text[:500])  # Affiche les 500 premiers caractères du wikitext
