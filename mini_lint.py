"""mini_lint.py: refuse covariates that sit on a derivation path to or from the target."""
import argparse
import sys
from collections import deque
from itertools import combinations

import yaml

RANK = {"certain": 3, "documented": 2, "inferred": 1}
DETERMINISTIC = {"component", "identity", "denominator"}


def fail(message):
    """Exit code 2 means the manifest or the command itself is broken."""
    print(message, file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------- step 1
class StrictLoader(yaml.SafeLoader):
    """A YAML loader that stops on a repeated key."""


def refuse_duplicates(loader, node, deep=False):
    seen = {}
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        line = key_node.start_mark.line + 1
        if key in seen:
            fail(f"manifest error: key {key!r} appears twice "
                 f"(line {seen[key]} and line {line})")
        seen[key] = line
    return loader.construct_mapping(node, deep=deep)


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, refuse_duplicates)


# ---------------------------------------------------------------- step 2
def load(path):
    try:
        with open(path) as fh:
            products = yaml.load(fh, StrictLoader)["products"]
    except (OSError, yaml.YAMLError, KeyError, TypeError) as e:
        fail(f"manifest error: unable to read {path}: {e}")

    edges = {}
    for name, product in products.items():
        edges[name] = []
        for e in product.get("derivesFrom") or []:
            if RANK.get(e.get("confidence")) is None:
                fail(f"manifest error: {name} has an edge with "
                     f"confidence {e.get('confidence')!r}")
            edges[name].append((e["variable"], e["relation"], e["confidence"]))
    return products, edges


# ---------------------------------------------------------------- step 3
def undefined_names(products, edges):
    mentioned = {parent for rows in edges.values() for parent, _, _ in rows}
    return sorted(mentioned - set(products))


def find_cycle(edges):
    state = {}

    def visit(node, stack):
        state[node] = "open"
        stack.append(node)
        for parent, _, _ in edges.get(node, []):
            if state.get(parent) == "open":
                return stack[stack.index(parent):] + [parent]
            if parent in state:
                continue
            cycle = visit(parent, stack)
            if cycle:
                return cycle
        stack.pop()
        state[node] = "closed"
        return None

    for node in edges:
        if node in state:
            continue
        cycle = visit(node, [])
        if cycle:
            return cycle
    return None


# ---------------------------------------------------------------- step 4
def ancestors(edges, node):
    """Every product that `node` was built from, at any distance."""
    found = set()
    queue = deque([node])
    while queue:
        current = queue.popleft()
        for parent, _, _ in edges.get(current, []):
            if parent in found:
                continue
            found.add(parent)
            queue.append(parent)
    return found


def routes(edges, start, goal):
    """Every path from start up to goal. Safe because step 3 ruled out cycles."""
    found = []
    for parent, relation, confidence in edges.get(start, []):
        step = (parent, relation, confidence)
        if parent == goal:
            found.append([step])
        else:
            for rest in routes(edges, parent, goal):
                found.append([step] + rest)
    return found


def describe(start, route):
    chain = " -> ".join([start] + [parent for parent, _, _ in route])
    weakest = min(route, key=lambda step: RANK[step[2]])[2]
    arithmetic = all(rel in DETERMINISTIC for _, rel, _ in route)
    kind = "deterministic" if arithmetic else "statistical"
    return [chain, f"{kind}, weakest link: {weakest}"]


# ---------------------------------------------------------------- step 5
def audit(products, edges, target, covariates):
    findings = []

    unknown = [n for n in [target, *covariates] if products.get(n) is None]
    if unknown:
        return [("ERROR", f"unknown name: {n}", ["check the spelling"])
                for n in unknown]

    target_ancestors = ancestors(edges, target)
    for cov in covariates:
        if cov in target_ancestors:
            found = routes(edges, target, cov)
            details = [line for r in found for line in describe(target, r)]
            findings.append(("ERROR", f"{cov} is an ancestor of the target "
                                      f"({len(found)} route(s))", details))
        if target in ancestors(edges, cov):
            found = routes(edges, cov, target)
            details = [line for r in found for line in describe(cov, r)]
            findings.append(("ERROR", f"{cov} is a descendant of the target "
                                      f"({len(found)} route(s))", details))

    for a, b in combinations(covariates, 2):
        if a in ancestors(edges, b) or b in ancestors(edges, a):
            findings.append(("ERROR", f"{a} and {b}: one is built from the other", []))
        elif ancestors(edges, a) & ancestors(edges, b):
            shared = sorted(ancestors(edges, a) & ancestors(edges, b))
            findings.append(("WARN", f"{a} and {b} share ancestors", shared))
    return findings


# ---------------------------------------------------------------- step 6
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="mini-manifest.yaml")
    parser.add_argument("--target", required=True)
    parser.add_argument("--covariates", nargs="+", required=True)
    args = parser.parse_args()

    products, edges = load(args.manifest)
    missing = undefined_names(products, edges)
    if missing:
        fail(f"manifest error: undefined names: {', '.join(missing)}")
    cycle = find_cycle(edges)
    if cycle:
        fail(f"manifest error: cycle: {' -> '.join(cycle)}")

    findings = audit(products, edges, args.target, args.covariates)
    severities = {severity for severity, _, _ in findings}
    if "ERROR" in severities:
        verdict = "FAIL"
    elif "WARN" in severities:
        verdict = "REVIEW"
    elif ancestors(edges, args.target):
        verdict = "PASS"
    else:
        verdict = "UNTRACED"

    basis = products.get(args.target, {}).get("measurementBasis", "unknown")
    print(f"target      {args.target}  [{basis}]")
    print(f"covariates  {', '.join(args.covariates)}")
    print(f"verdict     {verdict}\n")
    for severity, message, details in findings:
        print(f"  {severity:<5} {message}")
        for line in details:
            print(f"        {line}")

    sys.exit(1 if verdict == "FAIL" else 0)


if __name__ == "__main__":
    main()
