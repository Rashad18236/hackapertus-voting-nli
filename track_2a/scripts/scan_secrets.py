"""Search the whole git history (every commit on every branch fetched) for anything that looks like a secret.

Run from anywhere inside the repository (fetch all branches first: git fetch origin '+refs/heads/*:refs/remotes/origin/*'):

    python3 track_2a/scripts/scan_secrets.py [--json OUT]

Scans every line added in any commit reachable from any ref (git log -p --all), and the names of
all files ever added. Looks for:

- known token formats: OpenAI/Anthropic-style "sk-...", Hugging Face "hf_...", GitHub "ghp_",
  "gho_", "github_pat_", Slack "xox?-", AWS "AKIA...", Google "AIza...", private key blocks, JWTs;
- a value assigned to a name containing KEY, TOKEN, SECRET, PASSWORD or AUTH (as in .env files,
  Python, YAML or JSON), and "Bearer <value>", when the value is at least 16 characters, not a
  placeholder, and not a plain word or path;
- files named .env (other than .env.example), *.pem, *.key, id_rsa.

A found value is never printed in full: only its first four characters and its length.
Exits 1 if anything is found.
"""

import argparse
import json
import re
import subprocess
import sys

TOKEN_FORMATS = {
    "sk- key": r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}",
    "Hugging Face token": r"\bhf_[A-Za-z0-9]{30,}",
    "GitHub token": r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}",
    "Slack token": r"\bxox[baprs]-[A-Za-z0-9-]{10,}",
    "AWS access key": r"\bAKIA[0-9A-Z]{16}\b",
    "Google API key": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "private key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "JWT": r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
}
ASSIGNED = re.compile(r"""(?i)\b([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|AUTH)[A-Z0-9_]*)["']?\s*[:=]\s*["']?"""
                      r"""([^\s"',;)}]{16,})""")
BEARER = re.compile(r"(?i)\bbearer\s+([A-Za-z0-9._~+/=-]{16,})")
# Placeholders and values that are not secrets (tests, examples, the sandbox's proxy, f-strings, code).
ALLOWED = re.compile(r"(?i)^(your|stub|dummy|ci-dummy|example|placeholder|xxx|<|\{|\$|proxy-injected|changeme|test"
                     r"|os\.environ|env\.|settings|none|null|true|false|f\"|self\.|args\.|key\b)")
BAD_FILES = re.compile(r"(^|/)\.env(\.(?!example$)[^/]*)?$|\.pem$|\.key$|(^|/)id_rsa")


def mask(value):
    return f"{value[:4]}... ({len(value)} characters)"


def looks_secret(value):
    if ALLOWED.match(value):
        return False
    if "(" in value or re.match(r"[A-Za-z_]\w*\.[A-Za-z_]", value) or "/" in value or value.startswith(("http", "{", "[")):
        return False  # code (a call or an attribute), a path or a URL
    classes = sum(bool(re.search(p, value)) for p in (r"[a-z]", r"[A-Z]", r"[0-9]"))
    return classes >= 2 and not re.fullmatch(r"[0-9a-f]{16,64}", value)  # plain hex: hashes and commit ids


def scan():
    log = subprocess.run(["git", "log", "-p", "--all", "--no-color", "-U0", "--format=commit %H"],
                         capture_output=True, text=True, errors="replace", check=True).stdout
    findings, commit, path, lines = [], None, None, 0
    for line in log.splitlines():
        if line.startswith("commit "):
            commit = line.split()[1][:10]
        elif line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else line[4:]
        elif line.startswith("+") and not line.startswith("+++"):
            lines += 1
            text = line[1:]
            for kind, pattern in TOKEN_FORMATS.items():
                for m in re.finditer(pattern, text):
                    findings.append({"commit": commit, "file": path, "kind": kind, "value": mask(m.group(0))})
            for m in ASSIGNED.finditer(text):
                if looks_secret(m.group(2)):
                    findings.append({"commit": commit, "file": path, "kind": f"value assigned to {m.group(1)}",
                                     "value": mask(m.group(2))})
            for m in BEARER.finditer(text):
                if looks_secret(m.group(1)):
                    findings.append({"commit": commit, "file": path, "kind": "Bearer value", "value": mask(m.group(1))})
    names = subprocess.run(["git", "log", "--all", "--diff-filter=A", "--name-only", "--format="],
                           capture_output=True, text=True, check=True).stdout.split()
    for name in sorted(set(names)):
        if BAD_FILES.search(name):
            findings.append({"commit": None, "file": name, "kind": "file that should not be committed", "value": ""})
    commits = subprocess.run(["git", "rev-list", "--all"], capture_output=True, text=True, check=True).stdout.split()
    refs = subprocess.run(["git", "for-each-ref", "--format=%(refname:short)"], capture_output=True, text=True,
                          check=True).stdout.split()
    return {"commits": len(commits), "refs": refs, "added_lines": lines, "files_ever_added": len(set(names)),
            "findings": findings}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json")
    args = ap.parse_args()
    report = scan()
    print(f"{report['commits']} commits on {len(report['refs'])} refs, {report['added_lines']} added lines, "
          f"{report['files_ever_added']} files ever added")
    for f in report["findings"]:
        print(f"  {f['kind']}: {f['file']} in {f['commit']}: {f['value']}")
    print(f"{len(report['findings'])} findings")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as out:
            json.dump(report, out, indent=1)
    sys.exit(1 if report["findings"] else 0)


if __name__ == "__main__":
    main()
