"""Independent verification gate for Jarvis. Standard library only.

    .venv\\Scripts\\python scripts\\verify.py                  offline gate (tests, spec, hygiene)
    .venv\\Scripts\\python scripts\\verify.py --phase 3        phase gate: everything up to phase 3 must be satisfied
    .venv\\Scripts\\python scripts\\verify.py --live           also run the live checks (network, microphone, models)
    .venv\\Scripts\\python scripts\\verify.py --mutate jarvis\\listen.py   are the tests strong enough to catch a broken file?
    .venv\\Scripts\\python scripts\\verify.py --audit          history of spec, approvals, sign-offs and deleted tests
    .venv\\Scripts\\python scripts\\verify.py --gate 3         has David approved the plan for phase 3?

Human only (refuse to run without a real keyboard):
    --approve N     David approves plans/PHASE-N.md
    --lock          David re-locks acceptance/spec.json after a spec change he approved

Nothing here reads a status that an agent wrote. A check is satisfied only when its named
tests exist and pass in a run made by this script, or its live command succeeds, or David
has signed it off in acceptance/signoffs.md.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "acceptance" / "spec.json"
LOCK = ROOT / "acceptance" / "spec.lock"
SIGNOFFS = ROOT / "acceptance" / "signoffs.md"
REPORT = ROOT / "acceptance" / "last-report.json"
APPROVALS = ROOT / ".agents" / "approvals"
PLANS = ROOT / "plans"
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
PY = str(VENV_PY if VENV_PY.exists() else sys.executable)

SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    re.compile(r"AQ\.[0-9A-Za-z_\-]{30,}"),
    re.compile(r"gsk_[0-9A-Za-z]{20,}"),
    re.compile(r"sk-[0-9A-Za-z]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⭐⭕️]")
BANNED_FONTS = {"inter", "arial", "roboto", "system-ui", "-apple-system", "segoe ui", "helvetica", "sans-serif"}
IMPORT_ALIASES = {"dotenv": "python-dotenv", "kokoro_onnx": "kokoro-onnx", "faster_whisper": "faster-whisper",
                  "cv2": "opencv-python-headless", "yaml": "pyyaml", "PIL": "pillow"}
ID_RE = re.compile(r"\bP\d+-[LH]?\d+\b")


class Report:
    def __init__(self) -> None:
        self.problems: list[str] = []
        self.warnings: list[str] = []

    def fail(self, msg: str) -> None:
        self.problems.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def run(cmd: list[str], cwd: Path = ROOT, timeout: int = 300) -> tuple[int, str]:
    try:
        done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                              encoding="utf-8", errors="replace")
        return done.returncode, (done.stdout or "") + (done.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    except FileNotFoundError as err:
        return 127, str(err)


def git(*args: str) -> str:
    code, out = run(["git", *args])
    return out.strip() if code == 0 else ""


def mask(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[key hidden]", text)
    return text


def parse_py(path: Path, rep: Report) -> ast.AST | None:
    """Parse a Python file. 'utf-8-sig' everywhere in this script because Windows PowerShell 5.1 writes a
    hidden byte-order mark into UTF-8 files; Python itself accepts it, so a checker that did not would
    crash on perfectly good files. A real syntax error becomes a problem message, not a traceback."""
    try:
        return ast.parse(path.read_text(encoding="utf-8-sig"))
    except SyntaxError as err:
        rep.fail(f"syntax error in {path.relative_to(ROOT).as_posix()}:{err.lineno}: {err.msg}")
        return None


def spec_hash() -> str:
    return hashlib.sha256(SPEC.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_spec() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8-sig"))


# ---------------------------------------------------------------- spec integrity

def check_lock(rep: Report) -> None:
    if not LOCK.exists():
        rep.fail("acceptance/spec.lock is missing. Only David may create it (verify.py --lock).")
        return
    locked = LOCK.read_text(encoding="utf-8-sig").split()[0]
    if locked != spec_hash():
        rep.fail("acceptance/spec.json no longer matches acceptance/spec.lock. The requirements were changed "
                 "without David's approval. Revert the change, or ask David to run verify.py --lock.")


def check_spec_shape(spec: dict, rep: Report) -> None:
    seen: set[str] = set()
    for c in spec["checks"]:
        cid = c.get("id", "?")
        if cid in seen:
            rep.fail(f"spec: duplicate check id {cid}")
        seen.add(cid)
        if not ID_RE.fullmatch(cid):
            rep.fail(f"spec: bad check id {cid}")
        kind = c.get("kind")
        needs = {"test": ["tests"], "live": ["cmd", "expect"], "human": ["steps"]}.get(kind)
        if needs is None:
            rep.fail(f"spec: {cid} has unknown kind {kind!r}")
            continue
        if "phase" not in c:
            rep.fail(f"spec: {cid} is missing 'phase'")
        for field in needs + ["claim"]:
            if not c.get(field):
                rep.fail(f"spec: {cid} is missing '{field}'")


REGISTER = ROOT / "docs" / "09-CHECK-REGISTER.md"


def render_register(spec: dict) -> str:
    """Human-readable list of every check, generated from spec.json so it cannot drift from it."""
    lines = ["# Check register", "",
             "Generated from `acceptance/spec.json` by `scripts/verify.py --render-register`. Do not edit by hand; "
             "verify.py fails if this file is out of date.", "",
             "Kinds: **test** = named automated tests must exist and pass. **live** = a script that uses the real "
             "network, models or speakers. **human** = David judges and signs in `acceptance/signoffs.md`.", ""]
    for phase in sorted({c["phase"] for c in spec["checks"]}):
        lines += [f"## Phase {phase}: {spec['phases'][str(phase)]}", ""]
        for c in (c for c in spec["checks"] if c["phase"] == phase):
            lines.append(f"### {c['id']} ({c['kind']}) {c['claim']}")
            if c["kind"] == "test":
                if c.get("must_assert"):
                    lines.append(f"- Must prove: {c['must_assert']}")
                lines += [f"- Test: `{t}`" for t in c["tests"]]
                if c.get("covers"):
                    lines.append("- Tests must touch: " + ", ".join(f"`{w}`" for w in c["covers"]))
            elif c["kind"] == "live":
                lines.append(f"- Command: `{' '.join(c['cmd'][1:])}` must print `{c['expect']}`")
            else:
                lines.append(f"- David does: {c['steps']}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def check_doc_ids(spec: dict, rep: Report) -> None:
    """The register matches the spec, and no document mentions a check id that does not exist."""
    expected = render_register(spec)
    if not REGISTER.exists() or REGISTER.read_text(encoding="utf-8-sig").replace("\r\n", "\n") != expected:
        rep.fail("docs/09-CHECK-REGISTER.md is missing or stale. Run: .venv\\Scripts\\python scripts\\verify.py --render-register")
    known = {c["id"] for c in spec["checks"]}
    docs = [*ROOT.glob("docs/*.md"), ROOT / "AGENTS.md", ROOT / "START-HERE.md", *ROOT.glob("plans/*.md")]
    for doc in docs:
        if doc.exists() and doc != REGISTER:
            for cid in sorted(set(ID_RE.findall(doc.read_text(encoding="utf-8-sig"))) - known):
                rep.fail(f"{doc.relative_to(ROOT).as_posix()} mentions {cid}, which is not in acceptance/spec.json")


# ---------------------------------------------------------------- tests

def run_pytest(rep: Report) -> tuple[dict[str, str], dict[str, int], str]:
    """Run the whole suite. Returns ({nodeid: passed|failed|skipped}, totals, output tail)."""
    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "junit.xml"
        code, out = run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml_path}"], timeout=900)
        results: dict[str, str] = {}
        totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
        if not xml_path.exists():
            rep.fail("pytest produced no results file. Output tail:\n" + "\n".join(out.splitlines()[-15:]))
            return results, totals, out
        # The file was written by pytest on this machine a moment ago, so it is trusted input
        # and the standard parser is fine (defusedxml would be one more package on a full disk).
        suite = ET.parse(xml_path).getroot()
        for case in suite.iter("testcase"):
            results[_nodeid(case.get("classname", ""), case.get("name", ""))] = (
                "failed" if case.find("failure") is not None or case.find("error") is not None
                else "skipped" if case.find("skipped") is not None else "passed")
        for s in suite.iter("testsuite"):
            for key in totals:
                totals[key] += int(s.get(key, 0))
    return results, totals, out


def _nodeid(classname: str, name: str) -> str:
    parts = classname.split(".")
    for i in range(len(parts), 0, -1):
        rel = "/".join(parts[:i]) + ".py"
        if (ROOT / rel).exists():
            return "::".join([rel, *parts[i:], name])
    return f"{classname}::{name}"


def matching(ref: str, results: dict[str, str]) -> list[str]:
    return [n for n in results if n == ref or n.startswith(ref + "[")]


def check_hollow_tests(rep: Report) -> dict[str, str]:
    """Every test must contain a real assertion; returns {nodeid_prefix: source} for the covers check."""
    sources: dict[str, str] = {}
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        text = path.read_text(encoding="utf-8-sig")
        tree = parse_py(path, rep)
        if tree is None:
            continue
        rel = path.relative_to(ROOT).as_posix()
        helpers = {n.name: ast.get_source_segment(text, n) or "" for n in ast.walk(tree)
                   if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("test_")}
        for node in ast.walk(tree):
            if not (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")):
                continue
            # A test may build the thing under test through a helper in the same file, so the
            # "reachable" source is the test plus the helpers it names (two levels deep).
            reachable = ast.get_source_segment(text, node) or ""
            for _ in range(2):
                reachable += "\n".join(src for name, src in helpers.items()
                                       if re.search(rf"\b{re.escape(name)}\b", reachable) and src not in reachable)
            sources[f"{rel}::{node.name}"] = reachable
            real = False
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assert):
                    test = sub.test
                    real = real or not (isinstance(test, ast.Constant) and bool(test.value))
                elif isinstance(sub, ast.Call):
                    func = ast.unparse(sub.func)
                    if func in {"pytest.raises", "pytest.fail", "pytest.warns"} or func.split(".")[-1].startswith("assert_"):
                        real = True
            if not real:
                rep.fail(f"hollow test (no real assertion): {rel}::{node.name}")
            for deco in node.decorator_list:
                if re.search(r"\b(skip|skipif|xfail)\b", ast.unparse(deco)):
                    rep.fail(f"test is skipped or xfail (not allowed): {rel}::{node.name}")
    return sources


def evaluate(spec: dict, results: dict[str, str], sources: dict[str, str], live: dict[str, tuple[bool, str]],
             rep: Report) -> dict[str, str]:
    signed = parse_signoffs()
    status: dict[str, str] = {}
    for c in spec["checks"]:
        cid, kind = c["id"], c["kind"]
        if kind == "test":
            found = [matching(ref, results) for ref in c["tests"]]
            missing = sum(1 for f in found if not f)
            names = [n for f in found for n in f]
            if any(results[n] != "passed" for n in names):
                status[cid] = "FAIL"
            elif missing == len(found):
                status[cid] = "PENDING"
            elif missing:
                status[cid] = "PARTIAL"
            else:
                status[cid] = "PASS"
                covers = c.get("covers")
                if covers:
                    for ref in c["tests"]:
                        base = ref.split("[")[0]
                        if not any(word in sources.get(base, "") for word in covers):
                            rep.fail(f"{cid}: test {base} never touches {covers}; it may be testing a stand-in")
                            status[cid] = "FAIL"
        elif kind == "live":
            if cid in live:
                ok, _ = live[cid]
                status[cid] = "PENDING" if ok is None else "PASS" if ok else "FAIL"
            else:
                status[cid] = "NOT-RUN"
        else:
            status[cid] = "SIGNED" if signed.get(cid) == "PASS" else "FAIL-SIGNED" if cid in signed else "AWAITING-HUMAN"
    return status


# ---------------------------------------------------------------- live and human

def run_live(spec: dict) -> dict[str, tuple[bool | None, str]]:
    out: dict[str, tuple[bool | None, str]] = {}
    for c in spec["checks"]:
        if c["kind"] != "live":
            continue
        cmd = [PY if part == "{py}" else part for part in c["cmd"]]
        print(f"  live {c['id']}: {' '.join(c['cmd'][1:])}", flush=True)
        t0 = time.perf_counter()
        code, text = run(cmd, timeout=c.get("timeout", 300))
        if code == 2 and "usage:" in text:  # live_checks.py does not know this check yet: not built
            out[c["id"]] = (None, "not built yet")
            print("       PENDING (live_checks.py has no such check yet)")
            continue
        ok = code == 0 and re.search(c["expect"], text) is not None
        out[c["id"]] = (ok, mask(text))
        print(f"       {'PASS' if ok else 'FAIL'} in {time.perf_counter() - t0:.1f}s")
        if not ok:
            print("       " + "\n       ".join(mask(text).splitlines()[-6:]))
    return out


def parse_signoffs() -> dict[str, str]:
    """Only lines below the '## Entries' heading count (the examples above it must not). Newest line wins."""
    result: dict[str, str] = {}
    if SIGNOFFS.exists():
        text = SIGNOFFS.read_text(encoding="utf-8-sig")
        entries = text.split("## Entries", 1)[1] if "## Entries" in text else ""
        for line in entries.splitlines():
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3 and ID_RE.fullmatch(parts[0]):
                result[parts[0]] = parts[1].upper()
    return result


# ---------------------------------------------------------------- hygiene

def tracked_files() -> list[Path]:
    """Everything git tracks plus new files not yet added (but never ignored ones), so nothing hides from the scans."""
    listed = git("ls-files", "--cached", "--others", "--exclude-standard")
    files = [ROOT / p for p in listed.splitlines()] if listed else [p for p in ROOT.rglob("*") if p.is_file()]
    return [f for f in files if f.exists() and "history" not in f.relative_to(ROOT).parts[:1]
            and ".venv" not in f.relative_to(ROOT).parts]


def check_hygiene(rep: Report) -> None:
    files = tracked_files()
    if git("ls-files", ".env"):
        rep.fail(".env is tracked by git. Remove it from the index (git rm --cached .env).")
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8-sig") if (ROOT / ".gitignore").exists() else ""
    for needed in [".env", ".venv/", "models/", "data/", "acceptance/last-report.json"]:
        if needed not in ignore:
            rep.fail(f".gitignore does not list {needed}")
    text_suffixes = {".py", ".md", ".txt", ".json", ".html", ".css", ".js", ".bat", ".ini", ".example", ".toml", ".yml"}
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        if f.suffix not in text_suffixes and f.name not in {".env.example", ".gitignore"}:
            continue
        try:
            text = f.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                rep.fail(f"possible secret in tracked file {rel} (pattern {pattern.pattern[:12]}...)")
        if rel.startswith("jarvis/static/") and f.suffix in {".html", ".css", ".js"}:
            if EMOJI.search(text):
                rep.fail(f"emoji or dingbat symbol in UI file {rel}. Use SVG line icons.")
            for match in re.finditer(r"font-family:\s*([^;}]+)", text):
                first = match.group(1).split(",")[0].strip().strip("'\"").lower()
                if first in BANNED_FONTS:
                    rep.fail(f"banned primary font '{first}' in {rel}")
    for need in ["tokens.json", "DESIGN.md"]:
        if not (ROOT / need).exists():
            rep.fail(f"{need} is missing (UI design source of truth)")
    check_python_safety(rep)
    check_declared_imports(rep)
    check_markdown_links(rep, files)


def check_python_safety(rep: Report) -> None:
    for path in sorted((ROOT / "jarvis").rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        tree = parse_py(path, rep)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in {"0.0.0.0", "::"}:
                rep.fail(f"{rel}:{node.lineno} binds to every network address. Servers must listen on 127.0.0.1 only.")
            if isinstance(node, ast.keyword) and node.arg == "shell" and isinstance(node.value, ast.Constant) and node.value.value:
                rep.fail(f"{rel}:{node.value.lineno} shell=True is forbidden. Use named tools with argument lists.")
            if isinstance(node, ast.Call):
                name = ast.unparse(node.func)
                if name in {"eval", "exec", "os.system"}:
                    rep.fail(f"{rel}:{node.lineno} {name}() is forbidden.")


def check_declared_imports(rep: Report) -> None:
    declared: set[str] = set()
    for req in ROOT.glob("requirements*.txt"):
        for line in req.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "-")):
                declared.add(re.split(r"[<>=!~\[; ]", line)[0].lower().replace("_", "-"))
    for path in sorted((ROOT / "jarvis").rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        tree = parse_py(path, rep)
        if tree is None:
            continue
        for node in ast.walk(tree):
            mods: list[str] = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                mods = [node.module.split(".")[0]]
            for mod in mods:
                if mod in sys.stdlib_module_names or mod in {"jarvis", "__future__"}:
                    continue
                pkg = IMPORT_ALIASES.get(mod, mod).lower().replace("_", "-")
                if pkg not in declared:
                    rep.fail(f"{rel} imports '{mod}' but no requirements*.txt declares '{pkg}'")


def check_markdown_links(rep: Report, files: list[Path]) -> None:
    for f in files:
        rel = f.relative_to(ROOT).parts
        if f.suffix != ".md" or rel[0] in {".agents", ".visual"}:
            continue
        for target in re.findall(r"\]\(([^)\s]+)\)", f.read_text(encoding="utf-8-sig")):
            if re.match(r"(https?:|mailto:|#)", target):
                continue
            path = re.sub(r"(#.*|:\d+)$", "", target)
            if path and not (f.parent / path).exists():
                rep.fail(f"broken link in {f.relative_to(ROOT).as_posix()}: {target}")


def check_disk(rep: Report) -> float:
    free = shutil.disk_usage(ROOT).free / 1e9
    if free < 0.15:
        rep.fail(f"disk almost full: {free:.2f} GB free on this drive. Builds and installs will fail oddly. Free space first.")
    elif free < 1.0:
        rep.warn(f"low disk: {free:.2f} GB free. Do not install packages above ~100 MB without telling David.")
    return free


# ---------------------------------------------------------------- mutation testing

MUTATIONS = {
    ast.Gt: ast.LtE, ast.Lt: ast.GtE, ast.GtE: ast.Lt, ast.LtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
}


class _Mutator(ast.NodeTransformer):
    def __init__(self, target: int | None):
        self.target, self.count, self.sites = target, 0, []

    def _hit(self, node: ast.AST, label: str) -> bool:
        index = self.count
        self.count += 1
        self.sites.append((index, getattr(node, "lineno", 0), label))
        return index == self.target

    def visit_Compare(self, node: ast.Compare):
        self.generic_visit(node)
        if len(node.ops) == 1 and type(node.ops[0]) in MUTATIONS:
            label = f"{type(node.ops[0]).__name__} -> {MUTATIONS[type(node.ops[0])].__name__}"
            if self._hit(node, label):
                node.ops = [MUTATIONS[type(node.ops[0])]()]
        return node

    def visit_BoolOp(self, node: ast.BoolOp):
        self.generic_visit(node)
        flipped = ast.Or if isinstance(node.op, ast.And) else ast.And
        if self._hit(node, f"{type(node.op).__name__} -> {flipped.__name__}"):
            node.op = flipped()
        return node

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, bool) and self._hit(node, f"{node.value} -> {not node.value}"):
            return ast.copy_location(ast.Constant(value=not node.value), node)
        return node

    def visit_BinOp(self, node: ast.BinOp):
        self.generic_visit(node)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            swapped = ast.Sub if isinstance(node.op, ast.Add) else ast.Add
            if self._hit(node, f"{type(node.op).__name__} -> {swapped.__name__}"):
                node.op = swapped()
        return node

    def visit_UnaryOp(self, node: ast.UnaryOp):
        self.generic_visit(node)
        if isinstance(node.op, ast.Not) and self._hit(node, "not removed"):
            return node.operand
        return node


def mutate(target_rel: str, sample: int, min_score: float, rep: Report) -> None:
    target = ROOT / target_rel
    if not target.exists():
        rep.fail(f"--mutate: {target_rel} does not exist")
        return
    source = target.read_text(encoding="utf-8-sig")
    probe = _Mutator(None)
    probe.visit(ast.parse(source))
    sites = probe.sites
    if not sites:
        rep.fail(f"--mutate: no mutable operators found in {target_rel}")
        return
    rng = random.Random(1)
    chosen = sorted(rng.sample(sites, min(sample, len(sites))))
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "p"
        work.mkdir()
        for name in ["jarvis", "tests"]:
            shutil.copytree(ROOT / name, work / name, ignore=shutil.ignore_patterns("__pycache__", "models"))
        shutil.copy(ROOT / "pytest.ini", work / "pytest.ini")
        code, out = run([PY, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"], cwd=work, timeout=300)
        if code != 0:
            rep.fail("--mutate: tests are not green on an untouched copy, so mutation results would mean nothing.\n"
                     + "\n".join(out.splitlines()[-8:]))
            return
        killed, survivors = 0, []
        for index, line, label in chosen:
            mutator = _Mutator(index)
            mutated = ast.fix_missing_locations(mutator.visit(ast.parse(source)))
            (work / target_rel).write_text(ast.unparse(mutated), encoding="utf-8")
            code, _ = run([PY, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"], cwd=work, timeout=120)
            if code != 0:
                killed += 1
            else:
                survivors.append((line, label))
            print(f"  mutation {target_rel}:{line} {label}: {'caught' if code != 0 else 'SURVIVED'}", flush=True)
    score = killed / len(chosen)
    print(f"\nmutation score for {target_rel}: {killed}/{len(chosen)} caught ({score:.0%})")
    if survivors:
        print("survivors (read these: each is a behaviour no test noticed changing):")
        for line, label in survivors:
            print(f"  line {line}: {label}")
    if score < min_score:
        rep.fail(f"mutation score {score:.0%} for {target_rel} is below {min_score:.0%}: the tests do not pin this file's behaviour")


# ---------------------------------------------------------------- human-only commands

def need_human(action: str) -> None:
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print(f"REFUSED: {action} must be run by David at a real keyboard, not by an agent or script.")
        sys.exit(2)


def approve(phase: int) -> int:
    need_human(f"--approve {phase}")
    plan = PLANS / f"PHASE-{phase}.md"
    if not plan.exists():
        print(f"{plan.relative_to(ROOT)} does not exist. Ask the agent to write the plan first.")
        return 1
    text = plan.read_text(encoding="utf-8-sig")
    print("\n".join(text.splitlines()[:70]))
    print(f"\n... ({len(text.splitlines())} lines in total; read all of {plan.relative_to(ROOT)} before approving)")
    if input(f"\nType APPROVE PHASE {phase} to approve exactly this plan: ").strip() != f"APPROVE PHASE {phase}":
        print("Not approved.")
        return 1
    APPROVALS.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(text.replace("\r\n", "\n").encode()).hexdigest()
    (APPROVALS / f"PHASE-{phase}.approved").write_text(
        f"plan_sha256: {digest}\napproved: {datetime.now():%Y-%m-%d %H:%M}\n", encoding="utf-8")
    print(f"Approved. If the plan changes later, this approval stops matching and the agent must ask again.")
    return 0


def gate(phase: int, rep: Report) -> None:
    approval = APPROVALS / f"PHASE-{phase}.approved"
    plan = PLANS / f"PHASE-{phase}.md"
    if not approval.exists() or not plan.exists():
        rep.fail(f"No approved plan for phase {phase}. Write plans/PHASE-{phase}.md and ask David to run: "
                 f".venv\\Scripts\\python scripts\\verify.py --approve {phase}")
        return
    recorded = re.search(r"plan_sha256:\s*(\w+)", approval.read_text(encoding="utf-8-sig"))
    current = hashlib.sha256(plan.read_text(encoding="utf-8-sig").replace("\r\n", "\n").encode()).hexdigest()
    if not recorded or recorded.group(1) != current:
        rep.fail(f"plans/PHASE-{phase}.md changed after David approved it. Ask him to approve the new version.")


def relock() -> int:
    need_human("--lock")
    print(f"New spec hash: {spec_hash()}")
    print("Review the change first:  git diff acceptance/spec.json")
    if input("Type LOCK SPEC to accept the current acceptance/spec.json: ").strip() != "LOCK SPEC":
        print("Not locked.")
        return 1
    LOCK.write_text(f"{spec_hash()}  locked {datetime.now():%Y-%m-%d %H:%M}\n", encoding="utf-8")
    print("Locked.")
    return 0


def audit() -> int:
    print("== changes to the spec, lock, approvals and sign-offs (David should recognise every one) ==")
    print(git("log", "--format=%h %ad %an  %s", "--date=short", "--",
              "acceptance/spec.json", "acceptance/spec.lock", "acceptance/signoffs.md", ".agents/approvals") or "(none)")
    print("\n== tests deleted from the repository ==")
    print(git("log", "--diff-filter=D", "--format=%h %ad %s", "--date=short", "--name-only", "--", "tests") or "(none)")
    print("\n== number of test functions per commit that touched tests/ (should never go down) ==")
    for line in git("log", "--format=%h %ad %s", "--date=short", "--", "tests").splitlines():
        sha = line.split()[0]
        count = len(git("grep", "-h", "def test_", sha, "--", "tests").splitlines())
        print(f"  {count:3d} tests  {line}")
    return 0


# ---------------------------------------------------------------- main

def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", type=int, help="phase gate: every check up to this phase must be satisfied (implies --live)")
    ap.add_argument("--live", action="store_true", help="also run live checks")
    ap.add_argument("--mutate", metavar="FILE", help="mutation-test one module, e.g. jarvis/listen.py")
    ap.add_argument("--sample", type=int, default=15, help="number of mutations to try (default 15)")
    ap.add_argument("--min-score", type=float, default=0.6, help="share of mutations that must be caught (default 0.6)")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--render-register", action="store_true", help="rewrite docs/09-CHECK-REGISTER.md from the spec")
    ap.add_argument("--gate", type=int, metavar="N")
    ap.add_argument("--approve", type=int, metavar="N")
    ap.add_argument("--lock", action="store_true")
    args = ap.parse_args()

    if args.approve is not None:
        return approve(args.approve)
    if args.lock:
        return relock()
    if args.audit:
        return audit()
    if args.render_register:
        REGISTER.write_text(render_register(load_spec()), encoding="utf-8", newline="\n")
        print(f"wrote {REGISTER.relative_to(ROOT).as_posix()}")
        return 0

    rep = Report()
    if args.gate is not None:
        gate(args.gate, rep)
        print("GATE: PASS" if not rep.problems else "GATE: FAIL\n  " + "\n  ".join(rep.problems))
        return 1 if rep.problems else 0
    if args.mutate:
        mutate(args.mutate.replace("\\", "/"), args.sample, args.min_score, rep)
        print("MUTATE: PASS" if not rep.problems else "MUTATE: FAIL\n  " + "\n  ".join(rep.problems))
        return 1 if rep.problems else 0

    print(f"Jarvis verification  ({datetime.now():%Y-%m-%d %H:%M})  python: {PY}")
    free = check_disk(rep)
    check_lock(rep)
    spec = load_spec()
    check_spec_shape(spec, rep)
    check_doc_ids(spec, rep)
    sources = check_hollow_tests(rep)
    check_hygiene(rep)

    print("running the full test suite ...", flush=True)
    results, totals, out = run_pytest(rep)
    passed = sum(1 for v in results.values() if v == "passed")
    print(f"  {passed} passed, {totals['failures'] + totals['errors']} failed, {totals['skipped']} skipped")
    if totals["failures"] or totals["errors"]:
        rep.fail("the test suite has failures:\n" + "\n".join(out.splitlines()[-25:]))
    if totals["skipped"] > spec.get("allowed_skips", 0):
        rep.fail(f"{totals['skipped']} tests were skipped (allowed: {spec.get('allowed_skips', 0)}). "
                 "A skipped test proves nothing; install what it needs.")
    if passed < spec["min_total_tests"]:
        rep.fail(f"only {passed} tests passed but the floor is {spec['min_total_tests']}. Tests were deleted or are not collected.")

    live: dict[str, tuple[bool, str]] = {}
    if args.live or args.phase is not None:
        print("running live checks (needs internet, microphone, speakers, downloaded models) ...", flush=True)
        live = run_live(spec)
    status = evaluate(spec, results, sources, live, rep)

    print("\nphase  satisfied  detail")
    names = spec["phases"]
    for phase in sorted({c["phase"] for c in spec["checks"]}):
        mine = [c for c in spec["checks"] if c["phase"] == phase]
        ok = sum(1 for c in mine if status[c["id"]] in {"PASS", "SIGNED"})
        detail = ", ".join(f"{c['id']}={status[c['id']]}" for c in mine if status[c["id"]] not in {"PASS", "SIGNED"})
        print(f"  {phase:<4} {ok:>2}/{len(mine):<2}     {names.get(str(phase), '')}{'  | ' + detail if detail else ''}")

    for c in spec["checks"]:
        if status[c["id"]] in {"FAIL", "FAIL-SIGNED"}:
            rep.fail(f"check {c['id']} is {status[c['id']]}: {c['claim']}")
    if args.phase is not None:
        for c in spec["checks"]:
            if c["phase"] <= args.phase and status[c["id"]] not in {"PASS", "SIGNED"}:
                rep.fail(f"phase {args.phase} gate: {c['id']} is {status[c['id']]}: {c['claim']}")

    dirty = bool(git("status", "--porcelain"))
    if dirty:
        rep.warn("uncommitted changes: this result describes the working folder, not a commit.")
    REPORT.write_text(json.dumps({
        "time": datetime.now().isoformat(timespec="seconds"), "commit": git("rev-parse", "HEAD"), "dirty": dirty,
        "free_gb": round(free, 2), "tests_passed": passed, "status": status, "problems": rep.problems,
    }, indent=2), encoding="utf-8")

    for w in rep.warnings:
        print(f"WARNING: {w}")
    if rep.problems:
        print(f"\nVERIFY: FAIL ({len(rep.problems)} problem{'s' if len(rep.problems) != 1 else ''})")
        for p in rep.problems:
            print(f"  - {p}")
        return 1
    print("\nVERIFY: PASS" + (f" (phase {args.phase} gate)" if args.phase is not None else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
