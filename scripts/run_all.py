"""
WHAT THIS DOES
Runs the whole EDGAR pipeline (01 -> 11) with one command. Every script's
output is streamed live, and after each step the runner checks that the
files the step should have produced actually exist. Built to be verbose:
you always know which step is running, how long it has been going, what it
left on disk, and why anything was skipped.

ORDER
The default order is DEPENDENCY order, not numeric order:

    01 02 03 04   study universe (32 companies)
    05 06 09 10   S&P 500 universe, then fill big_cache/
    07 08 11      everything that READS big_cache/

07, 08 and 11 need the finished cache, so they run after 09/10. Plain
numeric order would run them against a half-filled cache and quietly give
you numbers based on ~180 companies instead of 503. Use --numeric to force
01 -> 11 anyway.

EXAMPLE
    python run_all.py                   # everything
    python run_all.py --dry-run         # print the plan and what's ready; run nothing
    python run_all.py --only 05 07      # just these steps
    python run_all.py --from 06         # step 06 onward, in the chosen order
    python run_all.py --skip 01 06      # everything except these
    python run_all.py --keep-going      # don't stop at the first failure
    python run_all.py --numeric         # strict 01..11 order

STEP STATUS
    OK    exit code 0 and every expected file present
    WARN  exit code 0 but something looks off (too few files, empty files,
          a file that was not rewritten). Worth reading, not fatal.
    FAIL  the script exited non-zero. Later steps are not run unless
          --keep-going is set.
    SKIP  an input the step needs is missing (says which one).

OUTPUT
Live progress, a per-step artifact report, a summary table, and a full log
at scripts/logs/run_<timestamp>.log.

COST OF A FULL RUN (fresh checkout)
~500 SEC requests, about 2 GB written to scripts/edgar_cache and
scripts/big_cache, roughly 10-20 minutes. Fetch steps skip anything already
on disk, so re-running is cheap.
"""
import argparse
import glob
import os
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(HERE, "logs")
HEARTBEAT_SECS = 15          # print "still running" after this much silence

# needs / makes are (glob relative to scripts/, minimum file count).
# "needs" that are missing => the step is SKIPPED instead of crashing.
# "makes" that fall short => WARN (the script itself decides pass/fail).
STEPS = {
    "01": dict(script="01_fetch.py",
               title="Fetch the 32-company study universe from SEC",
               needs=[],
               makes=[("edgar_cache/*.json", 33)]),
    "02": dict(script="02_analyze.py",
               title="Tag coverage study across the 32 companies",
               needs=[("edgar_cache/*.json", 30)],
               makes=[("coverage_raw.csv", 1), ("tag_usage.csv", 1)]),
    "03": dict(script="03_discover.py",
               title="Discover tags for the known gap fields",
               needs=[("edgar_cache/*.json", 30)],
               makes=[]),
    "04": dict(script="04_validate.py",
               title="Validate the tag map + derivations (coverage after fixes)",
               needs=[("edgar_cache/*.json", 30)],
               makes=[("coverage_final.csv", 1)]),
    "05": dict(script="05_universe.py",
               title="Build the S&P 500 universe file",
               needs=[],
               makes=[("sp500_universe.json", 1)]),
    "06": dict(script="06_fetch_big.py",
               title="Fetch a ~180-company stratified sample",
               needs=[("sp500_universe.json", 1)],
               makes=[("big_cache/*.json", 150), ("cik_suspects.json", 1)]),
    "07": dict(script="07_seed.py",
               title="Build companies_seed.csv (revenue-CAGR company_type guess)",
               needs=[("sp500_universe.json", 1), ("big_cache/*.json", 1)],
               makes=[("companies_seed.csv", 1)]),
    "08": dict(script="08_harden.py",
               title="Find tag gaps across every cached company",
               needs=[("sp500_universe.json", 1), ("big_cache/*.json", 1),
                      ("../configs/xbrl_tags.yaml", 1)],
               makes=[("gaps.json", 1)]),
    "09": dict(script="09_fetch_remaining.py",
               title="Fetch every remaining S&P 500 company",
               needs=[("sp500_universe.json", 1)],
               makes=[("big_cache/*.json", 490), ("cik_suspects.json", 1)]),
    "10": dict(script="10_retry_failed.py",
               title="Retry tickers that failed in step 09",
               needs=[("sp500_universe.json", 1), ("big_cache/*.json", 1),
                      ("cik_suspects.json", 1)],
               makes=[("big_cache/*.json", 490)]),
    "11": dict(script="11_matrix.py",
               title="Build the data-quality matrix (company x field)",
               needs=[("sp500_universe.json", 1), ("big_cache/*.json", 1)],
               makes=[("data_quality_matrix.csv", 1)]),
}

DEPENDENCY_ORDER = ["01", "02", "03", "04", "05", "06", "09", "10", "07", "08", "11"]
NUMERIC_ORDER = sorted(STEPS)

_log = None


def say(msg=""):
    """Print and tee to the log file."""
    print(msg, flush=True)
    if _log:
        _log.write(msg + "\n")
        _log.flush()


# ── small helpers ────────────────────────────────────────────────────────────
def fmt_secs(s):
    m, sec = divmod(int(s), 60)
    return f"{m}m{sec:02d}s" if m else f"{sec}s"


def fmt_bytes(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def matches(pattern):
    return glob.glob(os.path.join(HERE, pattern))


def size_of(pattern):
    return sum(os.path.getsize(p) for p in matches(pattern))


def mtime_of(pattern):
    """mtime for a single concrete file, else None."""
    if "*" in pattern:
        return None
    files = matches(pattern)
    return os.path.getmtime(files[0]) if files else None


def unmet(needs):
    return [f"{pat} (need >= {n}, have {len(matches(pat))})"
            for pat, n in needs if len(matches(pat)) < n]


# ── running one step ─────────────────────────────────────────────────────────
def run_step(step_id, step):
    """Run one script, stream its output, check its artifacts. Returns a result dict."""
    script = step["script"]
    result = {"id": step_id, "script": script, "status": "OK", "secs": 0.0, "note": ""}

    say("")
    say("=" * 78)
    say(f"STEP {step_id}: {step['title']}")
    say(f"  script : {script}")
    say(f"  started: {datetime.now():%H:%M:%S}")

    missing = unmet(step["needs"])
    if missing:
        say("  needs  : NOT MET -> skipping")
        for m in missing:
            say(f"           - {m}")
        result["status"] = "SKIP"
        result["note"] = "missing input: " + missing[0]
        return result
    for pat, n in step["needs"]:
        say(f"  needs  : {pat} -> {len(matches(pat))} present (>= {n})   ok")

    before_counts = {pat: len(matches(pat)) for pat, _ in step["makes"]}
    before_mtime = {pat: mtime_of(pat) for pat, _ in step["makes"]}
    watch = next((pat for pat, _ in step["makes"] if "*" in pat), None)

    env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    proc = subprocess.Popen(
        [sys.executable, "-u", script], cwd=HERE, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )

    lines = queue.Queue()

    def pump():
        for raw in proc.stdout:
            lines.put(raw.rstrip("\n"))
        lines.put(None)

    threading.Thread(target=pump, daemon=True).start()

    say("  output :")
    start = last_output = time.time()
    try:
        while True:
            try:
                line = lines.get(timeout=1)
            except queue.Empty:
                if time.time() - last_output >= HEARTBEAT_SECS:
                    extra = f", {watch} now {len(matches(watch))} files" if watch else ""
                    say(f"  | ... still running ({fmt_secs(time.time() - start)}{extra})")
                    last_output = time.time()
                continue
            if line is None:
                break
            say(f"  | {line}")
            last_output = time.time()
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        say("  | ^C received, terminated the child process")
        result.update(status="FAIL", note="interrupted by user",
                      secs=time.time() - start, interrupted=True)
        return result

    result["secs"] = time.time() - start
    say(f"  finished in {fmt_secs(result['secs'])}, exit code {proc.returncode}")

    # artifact report
    warnings = []
    if step["makes"]:
        say("  produced:")
    for pat, minimum in step["makes"]:
        found = matches(pat)
        n = len(found)
        delta = n - before_counts[pat]
        wildcard = "*" in pat
        state = "OK  " if n >= minimum else "WARN"
        detail = (f"{n} files ({'+' if delta >= 0 else ''}{delta}), "
                  f"{fmt_bytes(size_of(pat))}") if wildcard else \
                 (f"{fmt_bytes(size_of(pat))}" if n else "MISSING")
        if n < minimum:
            warnings.append(f"{pat}: {n} < expected {minimum}")
        if not wildcard and n and proc.returncode == 0 and \
                before_mtime[pat] is not None and mtime_of(pat) == before_mtime[pat]:
            state = "WARN"
            detail += "  (existed before and was NOT rewritten by this run)"
            warnings.append(f"{pat}: not rewritten")
        say(f"    [{state}] {pat:<24} {detail}")

        empties = [os.path.basename(p) for p in found
                   if p.endswith(".json") and os.path.getsize(p) == 0]
        if empties:
            say(f"    [WARN] {len(empties)} zero-byte file(s), e.g. {', '.join(empties[:4])}"
                " -- failed writes; delete them and re-run (fetchers skip existing files)")
            warnings.append(f"{len(empties)} zero-byte files in {pat}")

    if proc.returncode != 0:
        result["status"] = "FAIL"
        result["note"] = f"exit code {proc.returncode}"
    elif warnings:
        result["status"] = "WARN"
        result["note"] = warnings[0]
    return result


# ── plan / summary printing ──────────────────────────────────────────────────
def cache_line(label, pattern):
    n = len(matches(pattern))
    return f"  {label:<22} {n:>4} files  {fmt_bytes(size_of(pattern))}"


def print_plan(order, dry_run):
    say("PLAN")
    will_make = set()           # patterns an earlier step in THIS plan will produce
    for sid in order:
        step = STEPS[sid]
        # a need counts as satisfiable if it's on disk now OR an earlier planned step makes it
        missing = [f"{pat} (need >= {n}, have {len(matches(pat))})"
                   for pat, n in step["needs"]
                   if len(matches(pat)) < n and pat not in will_make]
        if dry_run:
            flag = "ready" if not missing else "would SKIP (" + missing[0] + ")"
        else:
            flag = ""
        say(f"  {sid}  {step['script']:<24} {step['title']}")
        if flag:
            say(f"      -> {flag}")
        will_make.update(pat for pat, _ in step["makes"])
    say("")
    say("CURRENT DISK STATE")
    say(cache_line("scripts/edgar_cache", "edgar_cache/*.json"))
    say(cache_line("scripts/big_cache", "big_cache/*.json"))


def print_summary(results, not_run, total_secs, log_path):
    say("")
    say("=" * 78)
    say("SUMMARY")
    say(f"  {'ID':<4} {'STATUS':<6} {'TIME':<8} {'SCRIPT':<24} NOTE")
    for r in results:
        say(f"  {r['id']:<4} {r['status']:<6} {fmt_secs(r['secs']):<8} "
            f"{r['script']:<24} {r['note']}")
    for sid in not_run:
        say(f"  {sid:<4} {'NOT RUN':<6} {'-':<8} {STEPS[sid]['script']:<24} "
            "an earlier step failed (use --keep-going to continue)")
    counts = {s: sum(1 for r in results if r["status"] == s) for s in ("OK", "WARN", "FAIL", "SKIP")}
    say("")
    say(f"  {counts['OK']} ok, {counts['WARN']} warn, {counts['FAIL']} failed, "
        f"{counts['SKIP']} skipped, {len(not_run)} not run   |   total {fmt_secs(total_secs)}")
    say("")
    say("DISK STATE")
    say(cache_line("scripts/edgar_cache", "edgar_cache/*.json"))
    say(cache_line("scripts/big_cache", "big_cache/*.json"))
    if log_path:
        say(f"\nfull log: {log_path}")


# ── entry point ──────────────────────────────────────────────────────────────
def build_order(args):
    order = list(NUMERIC_ORDER if args.numeric else DEPENDENCY_ORDER)
    norm = lambda ids: [i.zfill(2) for i in ids]
    for group in (args.only, args.skip, [args.from_step] if args.from_step else []):
        bad = [i for i in norm(group or []) if i not in STEPS]
        if bad:
            sys.exit(f"unknown step id(s): {', '.join(bad)}   (valid: {', '.join(NUMERIC_ORDER)})")
    if args.from_step:
        order = order[order.index(args.from_step.zfill(2)):]
    if args.only:
        order = [i for i in order if i in norm(args.only)]
    if args.skip:
        order = [i for i in order if i not in norm(args.skip)]
    return order


def main():
    global _log
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="Run the EDGAR pipeline (steps 01-11) with verbose output.")
    ap.add_argument("--only", nargs="+", metavar="ID", help="run only these steps")
    ap.add_argument("--skip", nargs="+", metavar="ID", help="run everything except these steps")
    ap.add_argument("--from", dest="from_step", metavar="ID", help="start at this step")
    ap.add_argument("--numeric", action="store_true", help="strict 01..11 order instead of dependency order")
    ap.add_argument("--keep-going", action="store_true", help="continue after a failed step")
    ap.add_argument("--dry-run", action="store_true", help="show the plan and readiness, run nothing")
    ap.add_argument("--no-log", action="store_true", help="don't write a log file")
    args = ap.parse_args()

    order = build_order(args)
    if not order:
        sys.exit("nothing to run after applying --only/--skip/--from")

    log_path = None
    if not args.dry_run and not args.no_log:
        os.makedirs(LOG_DIR, exist_ok=True)
        log_path = os.path.join(LOG_DIR, f"run_{datetime.now():%Y%m%d_%H%M%S}.log")
        _log = open(log_path, "w", encoding="utf-8")

    say("EDGAR PIPELINE RUNNER")
    say(f"  python : {sys.executable}")
    say(f"  cwd    : {HERE}")
    say(f"  when   : {datetime.now():%Y-%m-%d %H:%M:%S}")
    say(f"  order  : {'numeric' if args.numeric else 'dependency'} -> {' '.join(order)}")
    say("")
    print_plan(order, args.dry_run)

    if args.dry_run:
        say("\n(dry run, nothing executed)")
        return 0

    t0 = time.time()
    results, not_run = [], []
    for pos, sid in enumerate(order):
        r = run_step(sid, STEPS[sid])
        results.append(r)
        if r.get("interrupted") or (r["status"] == "FAIL" and not args.keep_going):
            not_run = order[pos + 1:]
            break

    print_summary(results, not_run, time.time() - t0, log_path)
    if _log:
        _log.close()
    return 1 if any(r["status"] == "FAIL" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
