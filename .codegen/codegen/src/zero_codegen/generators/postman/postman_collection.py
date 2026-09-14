"""
Postman Collection Generator - Generates Postman collection + env JSON from OpenAPI

Output: platform/tests/postman/generated/{domain}.collection.json, {domain}.env.json
For use with Newman and Vitest integration (1 request = 1 operation).
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.openapi import resolve_ref
from ...utils.file import ensure_directory


def _get_expected_status(operation: Dict[str, Any], method: str) -> int:
    responses = operation.get("responses") or {}
    for code in ("201", "200", "204"):
        if code in responses:
            return int(code)
    if method.lower() == "post":
        return 201
    if method.lower() == "delete":
        return 204
    return 200


def _path_to_postman_vars(path_template: str) -> str:
    return re.sub(r"\{(\w+)\}", r"{{\1}}", path_template)


def _get_path_param_names(path_template: str) -> List[str]:
    return re.findall(r"\{(\w+)\}", path_template)


def _collect_params(spec: Dict[str, Any], operation: Dict[str, Any]) -> tuple:
    path_params = []
    query_params = []
    for p in operation.get("parameters") or []:
        if isinstance(p, dict) and "$ref" in p:
            resolved = resolve_ref(spec, p["$ref"])
            if not resolved:
                continue
            p = resolved
        name = p.get("name")
        if not name:
            continue
        if p.get("in") == "path":
            path_params.append(name)
        elif p.get("in") == "query":
            query_params.append({"key": name, "value": "{{%s}}" % name})
    return path_params, query_params


def _example_string_value(key: str, prop: Dict[str, Any]) -> Any:
    """Prefer OpenAPI example/enum/default; never emit unresolved {{var}} literals."""
    if "example" in prop:
        return prop["example"]
    if prop.get("enum"):
        return prop["enum"][0]
    if "default" in prop and prop["default"] is not None:
        return prop["default"]
    # Stable, non-placeholder defaults so Newman cannot pollute Dynamo with "{{name}}".
    defaults = {
        "name": "Newman Test",
        "email": "newman@example.com",
        "domain": "example.com",
        "industry": "software",
        "title": "Engineer",
        "status": "active",
        "notes": "",
        "description": "",
        "phone": "",
        "url": "https://example.com",
        "website": "https://example.com",
        "linkedinUrl": "",
        "logoUrl": "",
    }
    if key in defaults:
        return defaults[key]
    if key.endswith("Id") or key.endswith("Token"):
        return f"newman_{key}"
    return ""


def _build_request_body(spec: Dict[str, Any], operation: Dict[str, Any]) -> Optional[str]:
    rb = operation.get("requestBody")
    if not rb:
        return None
    if isinstance(rb, dict) and "$ref" in rb:
        rb = resolve_ref(spec, rb["$ref"]) or {}
    content = (rb or {}).get("content", {}).get("application/json", {})
    schema = content.get("schema")
    if not schema:
        return "{}"
    if isinstance(schema, dict) and "$ref" in schema:
        schema = resolve_ref(spec, schema["$ref"]) or {}
    props = (schema or {}).get("properties", {})
    if not props:
        return "{}"
    example = {}
    for key, prop in props.items():
        if isinstance(prop, dict) and "$ref" in prop:
            prop = resolve_ref(spec, prop["$ref"]) or prop
        if isinstance(prop, dict):
            if prop.get("type") == "string":
                example[key] = _example_string_value(key, prop)
            elif prop.get("type") == "number":
                example[key] = prop.get("example", prop.get("default", 0))
            elif prop.get("type") == "integer":
                example[key] = prop.get("example", prop.get("default", 0))
            elif prop.get("type") == "boolean":
                example[key] = prop.get("example", prop.get("default", False))
            elif "example" in prop:
                example[key] = prop["example"]
            else:
                example[key] = None
        else:
            example[key] = None
    return json.dumps(example, indent=2)


def _id_var_from_operation_id(operation_id: str) -> Optional[str]:
    m = re.match(r"^(create|get|update|delete|list)(.+)$", operation_id, re.I)
    if not m:
        return None
    resource = m.group(2)
    # Strip scope prefixes only when a remainder remains (AccountActivity → Activity;
    # do not turn getAccount into empty).
    for prefix in ("Org", "Exchange", "Market"):
        if resource.startswith(prefix) and len(resource) > len(prefix):
            resource = resource[len(prefix) :]
            break
    singular = singularize_simple(resource) if resource else ""
    if not singular:
        return None
    return singular[0].lower() + singular[1:] + "Id"


def singularize_simple(resource: str) -> str:
    """Lightweight plural→singular for Postman id var names."""
    if resource.endswith("ies") and len(resource) > 3:
        return resource[:-3] + "y"
    if resource.endswith("ses") and len(resource) > 3:
        return resource[:-2]  # statuses → status (approx)
    if resource.endswith("s") and len(resource) > 1 and not resource.endswith("ss"):
        return resource[:-1]
    return resource


def _build_postman_request(spec: Dict[str, Any], path_template: str, method: str, operation: Dict[str, Any]) -> Dict[str, Any]:
    operation_id = operation.get("operationId") or "%s %s" % (method.upper(), path_template)
    expected_status = _get_expected_status(operation, method)
    path_params, query_params = _collect_params(spec, operation)
    path_with_vars = _path_to_postman_vars(path_template)
    raw_url = "{{baseUrl}}" + path_with_vars
    if query_params:
        raw_url += "?" + "&".join("%s=%s" % (q["key"], q["value"]) for q in query_params)
    body = _build_request_body(spec, operation) if method.lower() in ("post", "put", "patch") else None

    id_var = _id_var_from_operation_id(operation_id)
    save_scripts: List[str] = []
    if id_var and method.lower() in ("post", "put"):
        # Chain created ids onto collection vars. Prefer resource-shaped fields
        # (leadId, pipelineConfigId, teamId) then fall back to data.id. Also set
        # plain `id` when the path uses /{id} (lead get/update).
        path_id_keys = sorted(
            {
                seg[1:-1]
                for seg in path_template.split("/")
                if seg.startswith("{") and seg.endswith("}") and seg[1:-1] != "orgId"
            }
        )
        set_lines = [
            "var j = pm.response.json();",
            "var _id = j.data && (j.data.%s || j.data.id || j.data.jobId || j.data.pipelineConfigId || j.data.teamId || j.data.memberId || j.data.opportunityId);"
            % id_var,
            "if (_id) { pm.collectionVariables.set('%s', _id); pm.environment.set('%s', _id); pm.collectionVariables.set('id', _id); pm.environment.set('id', _id); }"
            % (id_var, id_var),
        ]
        for pk in path_id_keys:
            if pk != id_var and pk != "id":
                set_lines.append(
                    "if (_id) { pm.collectionVariables.set('%s', _id); pm.environment.set('%s', _id); }"
                    % (pk, pk)
                )
        save_scripts.append(" ".join(set_lines))
    if id_var and method.lower() == "get" and operation_id.lower().startswith("list"):
        save_scripts.append(
            "var j = pm.response.json(); var items = (j.data && j.data.items) || []; "
            "if (items.length) { var it = items[0]; "
            "var id = it.%s || it.id; "
            "if (id) { pm.collectionVariables.set('%s', id); pm.environment.set('%s', id); "
            "pm.collectionVariables.set('id', id); pm.environment.set('id', id); } }"
            % (id_var, id_var, id_var)
        )
    elif id_var and method.lower() == "get" and operation_id.lower().startswith("get"):
        save_scripts.append(
            "var j = pm.response.json(); if (j.data) { "
            "var id = j.data.%s || j.data.id; "
            "if (id) { pm.collectionVariables.set('%s', id); pm.environment.set('%s', id); "
            "pm.collectionVariables.set('id', id); pm.environment.set('id', id); } }"
            % (id_var, id_var, id_var)
        )

    test_lines = [
        "pm.test('%s status %s', function () { pm.response.to.have.status(%s); });" % (operation_id, expected_status, expected_status),
        "pm.test('response has envelope', function () { var j = pm.response.json(); pm.expect(j).to.have.property('data'); });",
    ]
    test_lines.extend(save_scripts)

    request = {
        "name": operation_id,
        "request": {
            "method": method.upper(),
            "header": [{"key": "Content-Type", "value": "application/json"}] if body else [],
            "url": {
                "raw": raw_url,
                "host": ["{{baseUrl}}"],
                "path": [seg if not (seg.startswith("{") and seg.endswith("}")) else "{{%s}}" % seg[1:-1] for seg in path_template.split("/") if seg],
                "query": query_params,
            },
            "description": operation.get("summary") or operation.get("description") or "",
        },
        "event": [
            {"listen": "test", "script": {"exec": test_lines, "type": "text/javascript"}},
        ],
    }
    if body:
        request["request"]["body"] = {"mode": "raw", "raw": body}
    return request


def _build_collection(spec: Dict[str, Any], domain_name: str, base_url: str) -> Dict[str, Any]:
    path_params_all = set()
    by_tag = {}
    for path_template, path_item in (spec.get("paths") or {}).items():
        for param in _get_path_param_names(path_template):
            path_params_all.add(param)
        for method in ("get", "post", "put", "patch", "delete"):
            op = path_item.get(method)
            if not op:
                continue
            tag = (op.get("tags") or ["Default"])[0]
            req = _build_postman_request(spec, path_template, method, op)
            by_tag.setdefault(tag, []).append(req)

    variables = [
        {"key": "baseUrl", "value": base_url or "http://localhost:3000"},
        {"key": "orgId", "value": "test-org"},
        {"key": "accessToken", "value": ""},
    ]
    for p in sorted(path_params_all):
        if p != "orgId":
            variables.append({"key": p, "value": ""})

    item = [{"name": tag, "item": reqs} for tag, reqs in by_tag.items()]

    return {
        "info": {
            "name": spec.get("info", {}).get("title") or domain_name,
            "description": spec.get("info", {}).get("description") or "Generated from OpenAPI for %s" % domain_name,
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": variables,
        "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{accessToken}}", "type": "string"}]},
        "item": item,
    }


def _build_env(domain_name: str, base_url: str) -> Dict[str, Any]:
    return {
        "id": "env-%s" % domain_name,
        "name": "%s - Local" % domain_name,
        "values": [
            {"key": "baseUrl", "value": base_url or "http://localhost:3000", "type": "default", "enabled": True},
            {"key": "orgId", "value": "test-org", "type": "default", "enabled": True},
            {"key": "accessToken", "value": "", "type": "secret", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
    }


def _extract_var_refs(text: str) -> set:
    """Extract {{varName}} refs from a string."""
    return set(re.findall(r"\{\{\s*(\w+)\s*\}\}", text or ""))


def _build_vitest_content(spec: Dict[str, Any], domain_name: str, base_url: str) -> str:
    """Build Vitest test file: 1 it() per operation, 1:1 with Postman collection."""
    path_params_all = set()
    query_params_all = set()
    body_params_all = set()
    operations: List[tuple] = []

    for path_template, path_item in (spec.get("paths") or {}).items():
        for param in _get_path_param_names(path_template):
            path_params_all.add(param)
        for method in ("get", "post", "put", "patch", "delete"):
            op = path_item.get(method)
            if not op:
                continue
            path_params, query_params = _collect_params(spec, op)
            for q in query_params:
                query_params_all.add(q["key"])
            body = _build_request_body(spec, op) if method.lower() in ("post", "put", "patch") else None
            if body:
                body_params_all.update(_extract_var_refs(body))
            operation_id = op.get("operationId") or "%s %s" % (method.upper(), path_template)
            expected_status = _get_expected_status(op, method)
            id_var = _id_var_from_operation_id(operation_id) if method.lower() in ("post", "put") else None
            operations.append((operation_id, method.upper(), path_template, expected_status, body, id_var, query_params))

    all_param_names = sorted(path_params_all | query_params_all | body_params_all)
    var_entries = [
        '  baseUrl: "http://localhost:3000",',
        '  orgId: "test-org",',
        '  accessToken: "",',
    ]
    for p in all_param_names:
        if p not in ("baseUrl", "orgId", "accessToken"):
            var_entries.append('  %s: "",' % p)

    lines = [
        "/**",
        " * Postman-collection 1:1 Vitest tests for %s (generated)" % domain_name,
        " *",
        " * One it() = one API request. Add sample data to vars for e2e runs.",
        " * Run: pnpm test:e2e or pnpm test:suite:db",
        " * Requires: API server at baseUrl (default http://localhost:3000)",
        " */",
        "",
        'import { describe, it, expect } from "vitest";',
        "",
        "const vars: Record<string, string> = {",
    ] + var_entries + [
        "};",
        "",
        "function sub(s: string): string {",
        '  return s.replace(/\\{\\{([^}]+)\\}\\}/g, (_, k) => vars[k.trim()] ?? "");',
        "}",
        "",
        'describe("Postman / %s (1:1 generated)", () => {' % domain_name,
    ]

    for operation_id, method, path_template, expected_status, body, id_var, query_params in operations:
        path_with_vars = _path_to_postman_vars(path_template)
        raw_url = "{{baseUrl}}" + path_with_vars
        if query_params:
            raw_url += "?" + "&".join("%s=%s" % (q["key"], q["value"]) for q in query_params)
        url_ts = "sub(" + json.dumps(raw_url) + ")"

        body_ts = ""
        if body:
            body_escaped = json.dumps(body)
            body_ts = "body: sub(" + body_escaped + "),"

        save_id = ""
        if id_var:
            save_id = "\n    if (j?.data?.id) vars['%s'] = j.data.id;" % id_var

        headers_ts = (
            'headers: { "Content-Type": "application/json", ...(vars.accessToken ? { Authorization: `Bearer ${vars.accessToken}` } : {}) }'
            if body
            else "headers: vars.accessToken ? { Authorization: `Bearer ${vars.accessToken}` } : {}"
        )

        test_lines = [
            "",
            "  it(\"%s\", async () => {" % operation_id,
            "    const url = %s;" % url_ts,
            "    const res = await fetch(url, {",
            "      method: \"%s\"," % method,
            "      %s," % headers_ts,
        ]
        if body_ts:
            test_lines.append("      %s" % body_ts)
        test_lines.extend([
            "    });",
            "    expect(res.status).toBe(%s);" % expected_status,
        ])
        if expected_status != 204:
            test_lines.append("    const j = await res.json(); expect(j).toHaveProperty(\"data\");" + save_id)
        test_lines.append("  });")
        lines.extend(test_lines)

    lines.extend(["});", ""])
    return "\n".join(lines)


class PostmanCollectionGenerator(BaseGenerator):
    """
    Generates Postman collection and environment JSON per domain from OpenAPI.

    Output: platform/tests/postman/generated/{domain}.collection.json, {domain}.env.json
    """

    @property
    def name(self) -> str:
        return "Postman Collection Generator"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def type(self) -> str:
        return "postman_collection"

    def generate(self, context: GenerationContext) -> GenerateResult:
        self.validate_context(context)
        spec = context.spec
        domain_name = context.domain_name
        project_root = Path(context.config.paths.project_root)
        base_url = (spec.get("servers") or [{}])[0].get("url") or "http://localhost:3000"

        out_dir = project_root / "platform" / "tests" / "postman" / "generated"
        e2e_dir = project_root / "platform" / "tests" / "src" / "__e2e__"
        ensure_directory(out_dir)
        ensure_directory(e2e_dir)

        collection = _build_collection(spec, domain_name, base_url)
        env = _build_env(domain_name, base_url)
        vitest_content = _build_vitest_content(spec, domain_name, base_url)

        collection_path = out_dir / (str(domain_name) + ".collection.json")
        env_path = out_dir / (str(domain_name) + ".env.json")
        vitest_path = e2e_dir / ("postman-%s.e2e.test.ts" % domain_name)

        try:
            collection_path.write_text(json.dumps(collection, indent=2), encoding="utf-8")
            env_path.write_text(json.dumps(env, indent=2), encoding="utf-8")
            vitest_path.write_text(vitest_content, encoding="utf-8")
        except Exception as e:
            return GenerateResult(errors=[str(e)])

        return GenerateResult(files=[collection_path, env_path, vitest_path])
