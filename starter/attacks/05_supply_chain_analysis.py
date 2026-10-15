"""
Supply Chain Vulnerability Analysis.

Parses a Trivy JSON report and analyzes a Dockerfile for security issues.
Produces a structured risk assessment of the AI system's deployment pipeline.

Usage:
    python 05_supply_chain_analysis.py
    python 05_supply_chain_analysis.py --trivy-report ../06_trivy_report.json --dockerfile ../Dockerfile
"""
import json
import argparse
import os

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", "05_supply_chain")


def parse_trivy_report(path):
    """
    Parse a Trivy JSON report and extract vulnerability details.

    The Trivy JSON format has a "Results" array, where each result has:
    - "Target": what was scanned (e.g., "debian 13.4" or "Python")
    - "Type": scan type (e.g., "debian", "python-pkg")
    - "Vulnerabilities": array of vulnerability objects

    Each vulnerability has: VulnerabilityID, Severity, PkgName,
    InstalledVersion, FixedVersion, Title, Description

    Args:
        path: Path to Trivy JSON report

    Returns:
        List of vulnerability dictionaries
    """
    with open(path) as f:
        data = json.load(f)

    vulns = []

    for result in data.get("Results", []):
        target = result.get("Target", "")
        target_type = result.get("Type", "")
        for vuln in result.get("Vulnerabilities") or []:
            description = vuln.get("Description", "") or ""
            vulns.append({
                "id": vuln.get("VulnerabilityID", ""),
                "severity": (vuln.get("Severity") or "UNKNOWN").upper(),
                "package": vuln.get("PkgName", ""),
                "installed_version": vuln.get("InstalledVersion", ""),
                "fixed_version": vuln.get("FixedVersion", ""),
                "title": vuln.get("Title", ""),
                "description": description[:200],
                "target": target,
                "target_type": target_type,
            })

    return vulns


def analyze_dockerfile(path):
    """
    Analyze a Dockerfile for common security issues.

    Check for:
    1. Running as root (no USER directive) — HIGH
    2. Unpinned base image (no SHA256 digest) — MEDIUM
    3. COPY . (copies entire context including secrets) — MEDIUM
    4. No HEALTHCHECK — LOW
    5. Build tools left in production image — MEDIUM
    6. Unnecessary tools (curl, git) in production — LOW

    Args:
        path: Path to Dockerfile

    Returns:
        List of issue dictionaries with: issue, severity, detail, recommendation
    """
    with open(path) as f:
        content = f.read()
    lines = content.strip().split("\n")

    issues = []
    upper = content.upper()

    def has_directive(name):
        return any(line.strip().upper().startswith(name) for line in lines)

    # 1. Running as root (no USER directive) — HIGH
    if not has_directive("USER"):
        issues.append({
            "issue": "Container runs as root (no USER directive)",
            "severity": "HIGH",
            "detail": (
                "No USER instruction is present, so the process runs as UID 0. "
                "A compromise of the app (e.g. via the RAG service) gives the "
                "attacker root inside the container, easing escape and lateral "
                "movement."
            ),
            "recommendation": (
                "Create and switch to a non-root user, e.g. "
                "`RUN useradd -m appuser` then `USER appuser` before CMD."
            ),
        })

    # 2. Unpinned base image (no SHA256 digest) — MEDIUM
    from_lines = [l for l in lines if l.strip().upper().startswith("FROM")]
    if from_lines and not any("@sha256:" in l.lower() for l in from_lines):
        issues.append({
            "issue": "Base image not pinned to a digest",
            "severity": "MEDIUM",
            "detail": (
                f"Base image is referenced by a mutable tag "
                f"({from_lines[0].strip()}). The contents behind that tag can "
                "change, so builds are not reproducible and a poisoned upstream "
                "image could be pulled silently."
            ),
            "recommendation": (
                "Pin the base image by digest, e.g. "
                "`FROM python:3.11-slim@sha256:<digest>`."
            ),
        })

    # 3. COPY . (copies entire build context including secrets) — MEDIUM
    if any(l.strip().upper().startswith("COPY .") or
           l.strip().upper().startswith("COPY . ") or
           l.strip().upper().startswith("ADD .")
           for l in lines):
        issues.append({
            "issue": "COPY . copies the entire build context",
            "severity": "MEDIUM",
            "detail": (
                "`COPY . /app` pulls the whole build context into the image. "
                "Without a strict .dockerignore this can bake in .env files, "
                "API keys, the .git history, local checkpoints, and test data."
            ),
            "recommendation": (
                "Copy only what runtime needs and add a .dockerignore that "
                "excludes .env, .git, __pycache__, *.pt, and datasets."
            ),
        })

    # 4. No HEALTHCHECK — LOW
    if not has_directive("HEALTHCHECK"):
        issues.append({
            "issue": "No HEALTHCHECK defined",
            "severity": "LOW",
            "detail": (
                "Without a HEALTHCHECK, orchestrators cannot tell a hung or "
                "crashed container from a healthy one, delaying detection of a "
                "failed or compromised service."
            ),
            "recommendation": (
                "Add a HEALTHCHECK that probes the app, e.g. the /health "
                "endpoint on port 5001."
            ),
        })

    # 5. Build tools left in production image — MEDIUM
    build_tools = [t for t in ["build-essential", "gcc", "g++", "make"]
                   if t in content]
    if build_tools:
        issues.append({
            "issue": "Build tools remain in the production image",
            "severity": "MEDIUM",
            "detail": (
                f"Compiler/build tooling ({', '.join(build_tools)}) is installed "
                "in the final image. It enlarges the attack surface and lets an "
                "attacker compile exploits or native payloads at runtime."
            ),
            "recommendation": (
                "Use a multi-stage build: compile wheels in a builder stage and "
                "copy only the installed packages into a slim runtime image."
            ),
        })

    # 6. Unnecessary tools (curl, git) in production — LOW
    extra_tools = [t for t in ["curl", "git", "wget", "netcat", "nc"]
                   if f" {t}" in content or f"\n{t}" in content or
                   f"    {t}" in content]
    if extra_tools:
        issues.append({
            "issue": "Unnecessary network/VCS tools in the image",
            "severity": "LOW",
            "detail": (
                f"Tools useful for lateral movement and exfiltration "
                f"({', '.join(sorted(set(extra_tools)))}) are present in the "
                "runtime image and are not needed to serve the app."
            ),
            "recommendation": (
                "Remove curl/git/wget from the runtime image, or install them "
                "only in a transient build stage."
            ),
        })

    return issues


def generate_report(vulns, dockerfile_issues):
    """Generate a structured supply chain risk report."""
    # TODO: Generate a report dictionary with:
    # - "summary": total vulnerabilities, severity breakdown, dockerfile issue count
    # - "high_severity_vulnerabilities": list of HIGH severity CVEs (top 15)
    # - "python_specific": vulnerabilities in Python packages
    # - "dockerfile_issues": from analyze_dockerfile()
    # - "risk_assessment": overall risk level and key concerns

    severity_counts = {}
    for v in vulns:
        sev = v.get("severity", "UNKNOWN")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    severity_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1,
                     "UNKNOWN": 0}

    def has_fix(v):
        return bool(v.get("fixed_version"))

    high_severity = [v for v in vulns if v["severity"] in ("CRITICAL", "HIGH")]
    high_severity.sort(
        key=lambda v: (severity_rank.get(v["severity"], 0), has_fix(v)),
        reverse=True,
    )

    python_specific = [
        v for v in vulns
        if "python" in v.get("target_type", "").lower()
        or "python" in v.get("target", "").lower()
    ]

    critical = severity_counts.get("CRITICAL", 0)
    high = severity_counts.get("HIGH", 0)
    fixable_high = sum(1 for v in high_severity if has_fix(v))

    if critical > 0:
        overall = "CRITICAL"
    elif high > 0:
        overall = "HIGH"
    elif severity_counts.get("MEDIUM", 0) > 0:
        overall = "MEDIUM"
    else:
        overall = "LOW"

    dockerfile_high = any(i["severity"] == "HIGH" for i in dockerfile_issues)
    if dockerfile_high and overall in ("LOW", "MEDIUM"):
        overall = "HIGH"

    key_concerns = []
    if critical or high:
        key_concerns.append(
            f"{critical} CRITICAL and {high} HIGH severity OS/package "
            f"vulnerabilities ({fixable_high} HIGH have fixes available)."
        )
    if python_specific:
        key_concerns.append(
            f"{len(python_specific)} vulnerabilities in Python packages that "
            "ship the ML/RAG runtime."
        )
    if dockerfile_high:
        key_concerns.append(
            "Container runs as root, amplifying the impact of any RCE."
        )

    report = {
        "summary": {
            "total_vulnerabilities": len(vulns),
            "severity_breakdown": severity_counts,
            "dockerfile_issues": len(dockerfile_issues),
        },
        "high_severity_vulnerabilities": high_severity[:15],
        "python_specific": python_specific,
        "dockerfile_issues": dockerfile_issues,
        "risk_assessment": {
            "overall_risk": overall,
            "fixable_high_severity": fixable_high,
            "key_concerns": key_concerns,
        },
    }
    return report


def main():
    parser = argparse.ArgumentParser(description="Supply Chain Vulnerability Analysis")
    parser.add_argument(
        "--trivy-report",
        default=os.path.join(os.path.dirname(__file__), "..", "06_trivy_report.json"),
    )
    parser.add_argument(
        "--dockerfile",
        default=os.path.join(os.path.dirname(__file__), "..", "Dockerfile"),
    )
    parser.add_argument(
        "--output",
        default=os.path.join(RESULTS_DIR, "supply_chain_report.json"),
    )
    args = parser.parse_args()
    if not os.path.dirname(args.output):
        args.output = os.path.join(RESULTS_DIR, args.output)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    print("Parsing Trivy report...")
    vulns = parse_trivy_report(args.trivy_report)

    print("Analyzing Dockerfile...")
    dockerfile_issues = analyze_dockerfile(args.dockerfile)

    report = generate_report(vulns, dockerfile_issues)

    # Print summary
    print(f"\n{'=' * 50}")
    print("  SUPPLY CHAIN RISK ASSESSMENT")
    print(f"{'=' * 50}")
    s = report["summary"]
    print(f"\n  Total vulnerabilities: {s['total_vulnerabilities']}")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        count = s["severity_breakdown"].get(sev, 0)
        if count:
            print(f"    {sev}: {count}")

    print(f"\n  Dockerfile issues: {s['dockerfile_issues']}")
    print(f"{'=' * 50}")

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull report saved to {args.output}")


if __name__ == "__main__":
    main()
