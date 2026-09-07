"""
Tool-using analyst over the network data.

The model never sees free text about the business. It picks one tool, the
pipeline runs that tool against the CSVs, and the model writes the answer using
only the JSON the tool returned. It cannot invent a recommendation, only
narrate one.

Providers: GEMINI_API_KEY, GROQ_API_KEY or OPENAI_API_KEY (+ OPENAI_BASE_URL),
first one found wins. With no credentials the tab still works: a deterministic
keyword router picks the tool and templates compose the answer from the same
tool output, labelled as "no model".
"""
import csv, json, os, pathlib, re, urllib.request

BASE = pathlib.Path(__file__).resolve().parents[1]
DATA = BASE / "data"

# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------

def _rows(name):
    with open(DATA / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _branches():
    return _rows("master.csv")


def _cells():
    return _rows("opportunity_cells.csv")


def _find(branch):
    q = branch.strip().lower()
    for r in _branches():
        if r["shop_id"].lower() == q:
            return r
    hits = [r for r in _branches() if q in r["branch_name"].lower()]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        exact = [r for r in hits if r["branch_name"].lower() == q]
        return exact[0] if exact else hits[0]
    return None


def _slim(r):
    keep = ["shop_id", "brand", "branch_name", "emirate", "rating", "n_reviews",
            "sig_health", "sig_attract", "sig_cannib", "score", "recommendation",
            "stability", "robust", "duel", "worst_overlap_brand", "worst_overlap_km",
            "comp_2km", "demand_2km"]
    return {k: r.get(k) for k in keep if k in r}


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------

def list_branches(brand=None, recommendation=None, limit=10):
    rows = _branches()
    if brand:
        rows = [r for r in rows if brand.lower() in r["brand"].lower()]
    if recommendation:
        rows = [r for r in rows if r["recommendation"].upper() == recommendation.upper()]
    rows.sort(key=lambda r: float(r["score"]))
    return {"count": len(rows), "branches": [_slim(r) for r in rows[:int(limit)]]}


def get_branch(branch):
    r = _find(branch)
    if not r:
        return {"error": f"No branch found matching '{branch}'."}
    out = _slim(r)
    out["reason"] = r["reason"]
    return out


def compare(branch_a, branch_b):
    a, b = _find(branch_a), _find(branch_b)
    if not a or not b:
        return {"error": "One of the two branches does not exist."}
    return {
        "a": _slim(a), "b": _slim(b),
        "delta": {k: round(float(a[k]) - float(b[k]), 1)
                  for k in ("sig_health", "sig_attract", "sig_cannib", "score")},
        "healthier": a["shop_id"] if float(a["sig_health"]) > float(b["sig_health"]) else b["shop_id"],
    }


def find_whitespace(limit=8):
    cells = [c for c in _cells() if c["opportunity"] == "GROW"]
    cells.sort(key=lambda c: -int(c["demand"]))
    return {"count": len(cells), "cells": [
        {"cell_id": c["cell_id"], "zone": c["zone_name"] or c["cell_id"],
         "lat": round(float(c["lat"]), 4),
         "lon": round(float(c["lon"]), 4), "demand": int(c["demand"]),
         "competitors": int(c["competitors"]),
         "nearest_group_km": float(c["nearest_group_km"]),
         "reason": c["reason"]} for c in cells[:int(limit)]]}


def explain(branch):
    r = _find(branch)
    if not r:
        return {"error": f"No branch found matching '{branch}'."}
    return {
        "shop_id": r["shop_id"], "branch_name": r["branch_name"], "brand": r["brand"],
        "recommendation": r["recommendation"], "score": float(r["score"]),
        "contributions": {
            "health": float(r["c_health"]),
            "market_attractiveness": float(r["c_attract"]),
            "cannibalisation": float(r["c_cannib"]),
        },
        "signals": {"health_pct": float(r["sig_health"]),
                    "attractiveness_pct": float(r["sig_attract"]),
                    "cannibalisation_pct": float(r["sig_cannib"])},
        "stability_pct": float(r["stability"]), "robustness": r["robust"],
        "reason": r["reason"],
    }


def network_summary():
    rows = _branches()
    bd = [r for r in rows if r["brand"] == "Bedashing"]
    from collections import Counter
    return {
        "scored_branches": len(rows),
        "bedashing": dict(Counter(r["recommendation"] for r in bd)),
        "all_brands": dict(Counter(r["recommendation"] for r in rows)),
        "fragile": [r["branch_name"] for r in rows if r["robust"] == "FRAGILE"],
        "highest_cannibalisation": sorted(
            [{"branch": f"{r['brand']} {r['branch_name']}",
              "pct": float(r["sig_cannib"])} for r in rows],
            key=lambda x: -x["pct"])[:5],
    }


TOOLS = {
    "list_branches": list_branches, "get_branch": get_branch, "compare": compare,
    "find_whitespace": find_whitespace, "explain": explain,
    "network_summary": network_summary,
}

TOOL_SPEC = """
list_branches(brand?, recommendation?, limit?)  list branches, worst score first
get_branch(branch)                              full record for one branch
compare(branch_a, branch_b)                     compare two branches signal by signal
find_whitespace(limit?)                         GROW zones ranked by demand
explain(branch)                                 decompose one branch's score
network_summary()                               overall split and fragile branches
""".strip()


# --------------------------------------------------------------------------
# Model adapter
# --------------------------------------------------------------------------

def _post(url, payload, headers):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


class LLM:
    """Minimal adapter. The business logic must not depend on who serves the
    model, so the provider is swappable and detected from the environment."""

    def __init__(self):
        self.provider = None
        if os.getenv("GEMINI_API_KEY"):
            self.provider = "gemini"
        elif os.getenv("GROQ_API_KEY"):
            self.provider = "groq"
        elif os.getenv("OPENAI_API_KEY"):
            self.provider = "openai"

    @property
    def available(self):
        return self.provider is not None

    def complete(self, system, user):
        if self.provider == "gemini":
            key = os.environ["GEMINI_API_KEY"]
            model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            j = _post(f"https://generativelanguage.googleapis.com/v1beta/models/"
                      f"{model}:generateContent?key={key}",
                      {"system_instruction": {"parts": [{"text": system}]},
                       "contents": [{"parts": [{"text": user}]}],
                       "generationConfig": {"temperature": 0.2}}, {})
            return j["candidates"][0]["content"]["parts"][0]["text"]

        base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        key = os.environ["OPENAI_API_KEY"]
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if self.provider == "groq":
            base = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
            key = os.environ["GROQ_API_KEY"]
            model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        j = _post(f"{base}/chat/completions",
                  {"model": model, "temperature": 0.2,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}]},
                  {"Authorization": f"Bearer {key}"})
        return j["choices"][0]["message"]["content"]


SYSTEM_ROUTER = f"""You are the router of a salon network analyst.
You have EXACTLY these tools available:

{TOOL_SPEC}

Return ONLY a JSON object, with no surrounding text, of this shape:
{{"tool": "<name>", "args": {{...}}}}
If the question fits no tool, use network_summary."""

SYSTEM_WRITER = """You are a retail network analyst. You answer to a Head of
Operations who decides lease renewals.

STRICT RULES:
- Use ONLY the data in the JSON you are given. Add no outside knowledge.
- Always cite the identifier or name of every branch you mention.
- If the JSON does not contain the answer, say so plainly.
- Six sentences maximum. Business language, no technical jargon.
- Signals are network percentiles (0-100), not absolute units."""


# --------------------------------------------------------------------------
# Deterministic router (no-model mode)
# --------------------------------------------------------------------------

def _rule_route(q):
    s = q.lower()
    m = re.search(r"compare\s+(.+?)\s+(?:with|to|vs\.?|and)\s+(.+)", s)
    if m:
        return "compare", {"branch_a": m.group(1).strip(" ?."),
                           "branch_b": m.group(2).strip(" ?.")}
    if any(w in s for w in ("open", "new site", "new store", "new branch",
                            "opportunit", "whitespace", "white space", "expand",
                            "expansion", "where should we grow", "grow")):
        return "find_whitespace", {"limit": 8}
    if any(w in s for w in ("why", "explain", "reason", "rationale")):
        for r in _branches():
            if r["branch_name"].lower() in s:
                return "explain", {"branch": r["branch_name"]}
    if any(w in s for w in ("close", "closure", "shrink", "downsize", "exit",
                            "worst", "cut")):
        return "list_branches", {"recommendation": "SHRINK", "limit": 10}
    if any(w in s for w in ("protect", "invest", "best", "strongest", "top")):
        return "list_branches", {"recommendation": "PROTECT", "limit": 10}
    if any(w in s for w in ("summary", "summarise", "summarize", "overview",
                            "how many", "split", "network")):
        return "network_summary", {}
    for r in _branches():
        if r["branch_name"].lower() in s:
            return "get_branch", {"branch": r["branch_name"]}
    return "network_summary", {}


def _template_answer(tool, result):
    """Deterministic wording from the same tool output a model would see."""
    if "error" in result:
        return result["error"]
    if tool == "network_summary":
        bd = result["bedashing"]
        return (f"The scored network covers {result['scored_branches']} women's-segment "
                f"salons. Bedashing: {bd.get('PROTECT',0)} to protect, "
                f"{bd.get('HOLD',0)} to hold and {bd.get('SHRINK',0)} to shrink. "
                f"Fragile recommendations: {', '.join(result['fragile']) or 'none'}. "
                f"Highest cannibalisation: " +
                "; ".join(f"{x['branch']} ({x['pct']:.0f}%)"
                          for x in result["highest_cannibalisation"][:3]) + ".")
    if tool == "list_branches":
        if not result["branches"]:
            return "No branches match that filter."
        ls = "; ".join(f"{b['brand']} {b['branch_name']} (score {b['score']}, "
                       f"{b['recommendation']})" for b in result["branches"])
        return f"{result['count']} branches match. Worst to best: {ls}."
    if tool in ("get_branch", "explain"):
        r = result
        return (f"{r.get('brand','')} {r.get('branch_name','')} [{r['recommendation']}]. "
                f"{r.get('reason','')} Recommendation stability: "
                f"{r.get('stability', r.get('stability_pct',''))}%.")
    if tool == "compare":
        a, b, d = result["a"], result["b"], result["delta"]
        return (f"{a['brand']} {a['branch_name']} sits at health percentile "
                f"{a['sig_health']} and {b['brand']} {b['branch_name']} at "
                f"{b['sig_health']} (gap {d['sig_health']:+}). "
                f"Score {a['score']} against {b['score']}. "
                f"The healthier of the two is {result['healthier']}.")
    if tool == "find_whitespace":
        cs = "; ".join(f"{c['zone']} with {c['demand']} retail POIs and "
                       f"{c['competitors']} competitors, nearest group site "
                       f"{c['nearest_group_km']} km away" for c in result["cells"][:4])
        return (f"There are {result['count']} zones classified GROW. Highest demand: {cs}.")
    return json.dumps(result, ensure_ascii=False)[:600]


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def ask(question, llm=None):
    """The answer, the tool it came from, and that tool's raw output."""
    llm = llm or LLM()
    used_model = False

    if llm.available:
        try:
            raw = llm.complete(SYSTEM_ROUTER, question)
            m = re.search(r"\{.*\}", raw, re.S)
            plan = json.loads(m.group(0))
            tool, args = plan["tool"], plan.get("args", {})
            if tool not in TOOLS:
                raise ValueError(tool)
            used_model = True
        except Exception:
            tool, args = _rule_route(question)
    else:
        tool, args = _rule_route(question)

    # A model returns arguments the tool does not accept often enough that this
    # is not defensive programming: `compare` with invented argument names took
    # the whole app down once. Retry with the deterministic router's arguments,
    # then give up with a readable message rather than a traceback.
    result = None
    for attempt_args in (args, _rule_route(question)[1], {}):
        try:
            result = TOOLS[tool](**attempt_args)
            args = attempt_args
            break
        except TypeError:
            continue
    if result is None:
        tool, args = _rule_route(question)
        try:
            result = TOOLS[tool](**args)
        except TypeError:
            result = {"error": f"Could not run '{tool}' with the arguments given."}

    if llm.available and used_model:
        try:
            answer = llm.complete(
                SYSTEM_WRITER,
                f"User question:\n{question}\n\n"
                f"Output of tool {tool}:\n"
                f"{json.dumps(result, ensure_ascii=False)}")
            mode = f"model ({llm.provider})"
        except Exception:
            answer, mode = _template_answer(tool, result), "no model (provider failed)"
    else:
        answer, mode = _template_answer(tool, result), "no model (template)"

    return {"answer": answer, "tool": tool, "args": args,
            "tool_output": result, "mode": mode}


def narrate(shop_id, llm=None):
    """Branch summary anchored to the data. The model only sees signals."""
    llm = llm or LLM()
    facts = explain(shop_id)
    if "error" in facts:
        return facts["error"], "error"
    if not llm.available:
        return facts["reason"], "no model (template)"
    try:
        txt = llm.complete(
            SYSTEM_WRITER,
            "Write three sentences on the state of this branch for a lease "
            "renewal committee, using only this data:\n"
            + json.dumps(facts, ensure_ascii=False))
        return txt, f"model ({llm.provider})"
    except Exception:
        return facts["reason"], "no model (provider failed)"


if __name__ == "__main__":
    llm = LLM()
    print(f"Provider detected: {llm.provider or 'none -> no-model mode'}\n")
    for q in ["which branches should we close?",
              "where should we open a new site?",
              "compare Mirdif 35 with City Centre Mirdif",
              "why does Al Barsha get that recommendation?",
              "give me a summary of the network"]:
        r = ask(q, llm)
        print(f"Q: {q}")
        print(f"   tool: {r['tool']}({r['args']})   mode: {r['mode']}")
        print(f"   A: {r['answer']}\n")
