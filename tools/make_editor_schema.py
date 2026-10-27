"""Write schema/diagram.editor.schema.json: the map schema with every domain's terms
filled in as choices, so VS Code can autocomplete and flag wrong terms while you
type. Re-run after changing a domain file."""
import copy
import json

from lexicon import ROOT, SCHEMA, domain, domain_names

s = copy.deepcopy(SCHEMA)
union = lambda key: sorted({t for name in domain_names() for t in domain(name)[key]})
node = s["properties"]["nodes"]["items"]["properties"]
node["activity"]["enum"] = union("activities")
node["system"]["enum"] = union("systems")
node["lane"]["enum"] = union("lanes")
node["practices"]["items"] = {"enum": union("practices")}
s["properties"]["domain"]["enum"] = domain_names()
(ROOT / "schema" / "diagram.editor.schema.json").write_text(json.dumps(s, indent=2))
print("wrote schema/diagram.editor.schema.json")
