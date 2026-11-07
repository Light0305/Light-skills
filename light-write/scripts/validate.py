"""Offline structural checks; no model calls and no full JSON Schema engine."""

import argparse
import json
import math
import re
from pathlib import Path


class ValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def local_file(root, value):
    require(isinstance(value, str) and bool(value), "Path must be a nonempty string")
    require("\\" not in value and not value.startswith("/") and ":" not in value,
            f"Path must be root-relative POSIX: {value}")
    path = (root / value).resolve()
    require(path.is_relative_to(root.resolve()), f"Path escapes package: {value}")
    require(path.is_file(), f"Missing file: {value}")
    return path


def check_schema(value, schema, where="value"):
    """Validate only the keywords used in this package's JSON contracts."""
    types = {
        "object": lambda x: isinstance(x, dict),
        "array": lambda x: isinstance(x, list),
        "string": lambda x: isinstance(x, str),
        "integer": lambda x: isinstance(x, int) and not isinstance(x, bool),
        "number": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
        "boolean": lambda x: isinstance(x, bool),
        "null": lambda x: x is None,
    }
    if "type" in schema:
        allowed = schema["type"]
        allowed = [allowed] if isinstance(allowed, str) else allowed
        require(any(types[t](value) for t in allowed), f"{where}: expected {allowed}")
    if "const" in schema:
        require(value == schema["const"], f"{where}: invalid constant")
    if "enum" in schema:
        require(value in schema["enum"], f"{where}: invalid enum value")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            require(key in value, f"{where}: missing {key}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            require(not (value.keys() - properties.keys()), f"{where}: unknown fields")
        for key, child in value.items():
            if key in properties:
                check_schema(child, properties[key], f"{where}.{key}")
    elif isinstance(value, list):
        require(len(value) >= schema.get("minItems", 0), f"{where}: too few items")
        if schema.get("uniqueItems"):
            require(len({json.dumps(x, sort_keys=True) for x in value}) == len(value),
                    f"{where}: duplicate items")
        for index, child in enumerate(value):
            if "items" in schema:
                check_schema(child, schema["items"], f"{where}[{index}]")
    elif isinstance(value, str):
        require(len(value) >= schema.get("minLength", 0), f"{where}: empty string")
        if "pattern" in schema:
            require(re.search(schema["pattern"], value) is not None, f"{where}: invalid pattern")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        require(not isinstance(value, float) or math.isfinite(value), f"{where}: nonfinite number")
        require(value >= schema.get("minimum", float("-inf")), f"{where}: below minimum")
        require(value <= schema.get("maximum", float("inf")), f"{where}: above maximum")


def parse_json(text, path):
    def reject_constant(value):
        raise ValidationError(f"Non-JSON numeric constant in {path}: {value}")

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    return json.loads(text, parse_constant=reject_constant,
                      object_pairs_hook=unique_keys)


def read_json(path):
    return parse_json(path.read_text(encoding="utf-8"), path)


def check_module(root, entry):
    path = local_file(root, entry["path"])
    require(path.suffix == ".md", f"Module must be Markdown: {path}")
    text = path.read_text(encoding="utf-8")
    require(f"- **ID:** {entry['id']}\n" in text, f"Module ID mismatch: {entry['id']}")
    require(f"- **Maturity:** {entry['maturity']}\n" in text,
            f"Maturity mismatch: {entry['id']}")
    for heading in ("Scope", "Out of scope", "Provenance", "Last reviewed"):
        require(f"- **{heading}:** " in text, f"Module metadata missing {heading}")
    for heading in ("Argument and evidence load", "Writing decisions", "Common failure modes",
                    "Interactions", "Sources and verification"):
        require(f"## {heading}\n" in text, f"Module section missing {heading}")
    for ref in entry["review_refs"] + entry["evaluation_refs"]:
        local_file(root, ref)
    if entry["maturity"] == "draft":
        require(not entry["review_refs"] and not entry["evaluation_refs"],
                "Draft module must not claim completed review/evaluation")
        require("- **Expert review record:** None" in text
                and "- **Evaluation record:** None" in text,
                "Draft module must disclose no review/evaluation record")
    else:
        require(bool(entry["review_refs"]), "Reviewed module needs a review record")
        if entry["maturity"] == "evaluated":
            require(bool(entry["evaluation_refs"]), "Evaluated module needs evaluation evidence")
    if entry["kind"] == "venue":
        require("## Official requirements\n" in text, "Venue module needs official-rule section")


def check_case(case, schema, module_ids):
    require(isinstance(case, dict), "case: expected object")
    check_schema(case, schema, case.get("id", "case"))
    require(set(case["expected_modules"]) <= module_ids,
            f"Unknown module in case: {case['id']}")


def check_run(record, schema, case_ids, root):
    require(isinstance(record, dict), "run: expected object")
    check_schema(record, schema, record.get("run_id", "run"))
    require(record["case_id"] in case_ids, "Run references unknown case")
    if record["arm"] == "baseline":
        require(record["skill_snapshot"] is None and not record["loaded_files"],
                "Baseline must not load skill guidance")
    else:
        require(bool(record["skill_snapshot"]), "Skill arm needs snapshot identifier")
    for item in record["loaded_files"]:
        # Paths are bundle-relative, not necessarily paths in the current skill.
        path = item["path"]
        require(not Path(path).is_absolute() and ":" not in path
                and "\\" not in path and ".." not in Path(path).parts,
                "Loaded-file path must remain within retained bundle")
    reviewer_ids = [r["reviewer_id"] for r in record["reviews"]]
    require(len(reviewer_ids) == len(set(reviewer_ids)), "Duplicate independent reviewer")


def check_document_paths(root):
    # Literal package paths only: templates contain instructional placeholders.
    pattern = re.compile(r"`((?:references|modules|standards|schemas|scripts|tests|templates|LICENSES)/[^`\s]+)`")
    count = 0
    for path in root.rglob("*.md"):
        # Evaluation bundles retain immutable external snapshots and model prose.
        # Their links are not relative to the current package; audit those bundles
        # using their recorded paths and hashes rather than interpreting them here.
        if any(part in {".claude", ".git", "__pycache__", "evaluations"} for part in path.relative_to(root).parts):
            continue
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            value = match.group(1)
            if any(char in value for char in "<>*[]") or value.endswith("/"):
                continue
            filename, _, anchor = value.partition("#")
            target = local_file(root, filename)
            if anchor:
                headings = re.findall(r"^#{1,6} (.+)$", target.read_text(encoding="utf-8"), re.M)
                slugs = [re.sub(r"[^\w -]", "", h.lower()).replace(" ", "-") for h in headings]
                require(anchor in slugs, f"Missing anchor: {value}")
            count += 1
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if target.startswith(("https://", "http://", "#")):
                continue
            # Markdown links follow the referring document, unlike literal
            # package paths in backticks, which follow the skill root.
            resolved = (path.parent / target.split("#")[0]).resolve()
            require(resolved.is_relative_to(root.resolve()), f"Link escapes package: {target}")
            require(resolved.is_file(), f"Missing document link: {path.name} -> {target}")
    return count


def validate(root, run_paths=()):
    for name in ("SKILL.md", "README.md", "README_EN.md", "CONTRIBUTING.md",
                 "THIRD_PARTY_NOTICES.md", "LICENSES/Apache-2.0.txt",
                 "standards/modules.md", "standards/evaluation.md",
                 "templates/field-module.md", "templates/venue-module.md", "tests/scenarios.md",
                 "references/latex-output.md", "scripts/latex_project.py",
                 "templates/latex/double-column.tex", "templates/latex/single-column.tex",
                 "templates/latex/common/lightwrite.sty", "templates/latex/common/language.tex",
                 "templates/latex/common/metadata.tex", "templates/latex/common/references.bib",
                 "templates/latex/common/sections/abstract.tex", "templates/latex/common/sections/body.tex"):
        local_file(root, name)
    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    require(re.match(r'\A---\nname: light-write\ndescription: [^\n]+\n'
                     r'(?:metadata:\n  version: "\d+\.\d+\.\d+"\n)?---\n', skill),
            "Invalid skill frontmatter")
    schemas = {name: read_json(local_file(root, f"schemas/{name}.schema.json"))
               for name in ("module", "case", "run")}
    catalog = read_json(local_file(root, "modules/catalog.json"))
    check_schema(catalog, schemas["module"], "catalog")
    ids, module_paths = set(), set()
    for entry in catalog["modules"]:
        require(entry["id"] not in ids, f"Duplicate module ID: {entry['id']}")
        require(entry["path"] not in module_paths, "Module paths must be distinct")
        ids.add(entry["id"])
        module_paths.add(entry["path"])
        check_module(root, entry)
    case_ids, covered = set(), set()
    lines = local_file(root, "tests/cases.jsonl").read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines, 1):
        require(bool(line.strip()), f"Blank JSONL row {index}")
        case = parse_json(line, f"tests/cases.jsonl:{index}")
        check_case(case, schemas["case"], ids)
        require(case["id"] not in case_ids, f"Duplicate case ID: {case['id']}")
        case_ids.add(case["id"])
        covered.update(case["expected_modules"])
    require(bool(case_ids), "No cases")
    require(ids <= covered, "Every catalog module needs a development case")
    for path in run_paths:
        check_run(read_json(path), schemas["run"], case_ids, root)
    references = check_document_paths(root)
    print(f"PASS: {len(ids)} modules, {len(case_ids)} cases, {references} document paths/anchors, "
          f"3 JSON contracts, {len(run_paths)} supplied run records")
    print("Structural subset checks only: no model execution, expert review, or quality score.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--run", type=Path, action="append", default=[],
                        help="Optional generation record JSON to structurally check")
    args = parser.parse_args()
    try:
        validate(args.root.resolve(), args.run)
    except (ValidationError, OSError, json.JSONDecodeError) as error:
        parser.exit(1, f"FAIL: {error}\n")


if __name__ == "__main__":
    main()
