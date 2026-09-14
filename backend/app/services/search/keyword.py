"""Boolean keyword query DSL: `python fastapi`, `python AND fastapi`,
`python OR java`, `python -php`, and quoted phrases like `"machine learning"`.

The query is parsed into OR-groups of (term, include) pairs: a candidate
matches if it satisfies ALL terms in at least one OR-group (include terms
must be present, exclude terms must be absent).
"""

import shlex


def parse_query(query: str) -> list[list[tuple[str, bool]]]:
    try:
        tokens = shlex.split(query)
    except ValueError:
        tokens = query.split()

    groups: list[list[tuple[str, bool]]] = [[]]
    for tok in tokens:
        upper = tok.upper()
        if upper == "OR":
            groups.append([])
            continue
        if upper == "AND":
            continue
        include = True
        if tok.startswith("-") and len(tok) > 1:
            include = False
            tok = tok[1:]
        if tok:
            groups[-1].append((tok.lower(), include))
    return [g for g in groups if g]


class KeywordSearch:
    """Evaluates the boolean query DSL against a plain-text document per candidate."""

    def matches(self, document: str, groups: list[list[tuple[str, bool]]]) -> bool:
        if not groups:
            return True
        doc = document.lower()
        for group in groups:
            if all((term in doc) == include for term, include in group):
                return True
        return False

    def score(self, document: str, groups: list[list[tuple[str, bool]]]) -> float:
        """Fraction of include-terms (across the best-matching OR-group) found in the doc.
        Used purely for relevance ranking among candidates that already passed `matches`."""
        if not groups:
            return 0.0
        doc = document.lower()
        best = 0.0
        for group in groups:
            include_terms = [t for t, inc in group if inc]
            if not include_terms:
                continue
            hits = sum(1 for t in include_terms if t in doc)
            best = max(best, hits / len(include_terms))
        return best
