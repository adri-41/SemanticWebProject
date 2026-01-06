import mwparserfromhell

def extract_infobox(wikitext, template_name="Infobox character"):
    wikicode = mwparserfromhell.parse(wikitext)
    for tpl in wikicode.filter_templates():
        if tpl.name.matches(template_name):
            return {param.name.strip(): str(param.value).strip() for param in tpl.params}
    return {}

# Exemple
from src.crawl import page
infobox = extract_infobox(page.text())
print(infobox)
