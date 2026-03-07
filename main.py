#!/usr/bin/env python3
"""Agent Improvement Loop — Perceive, Reason, Act, Refine."""
import json, os, random, hashlib, datetime

DOMAINS = [
    {"name": "code_review", "signals": ["complexity", "duplication", "coverage"]},
    {"name": "incident_response", "signals": ["severity", "blast_radius", "mttr"]},
    {"name": "data_pipeline", "signals": ["freshness", "schema_drift", "volume_anomaly"]},
    {"name": "deployment", "signals": ["rollback_rate", "canary_error", "latency_p99"]},
]

def perceive(domain):
    readings = {s: round(random.uniform(0, 1), 4) for s in domain["signals"]}
    readings["_hash"] = hashlib.sha256(json.dumps(readings, sort_keys=True).encode()).hexdigest()[:12]
    return readings

def reason(readings):
    alerts = [k for k, v in readings.items() if isinstance(v, float) and v > 0.75]
    risk = round(sum(v for v in readings.values() if isinstance(v, float)) / max(len([v for v in readings.values() if isinstance(v, float)]), 1), 4)
    return {"alerts": alerts, "risk_score": risk, "decision": "intervene" if risk > 0.6 else "monitor"}

def act(decision_pkg):
    actions = []
    if decision_pkg["decision"] == "intervene":
        for a in decision_pkg["alerts"]:
            actions.append({"action": f"mitigate_{a}", "priority": "high", "status": "executed"})
    else:
        actions.append({"action": "log_and_watch", "priority": "low", "status": "scheduled"})
    return actions

def refine(history):
    if len(history) < 2:
        return {"adjustment": "none", "reason": "insufficient_data"}
    recent = [h["reasoning"]["risk_score"] for h in history[-5:]]
    trend = "improving" if recent[-1] < recent[0] else "degrading"
    return {"adjustment": "tighten_thresholds" if trend == "degrading" else "maintain", "trend": trend, "window": len(recent)}

def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    log = {"timestamp": now.isoformat(), "cycle_id": hashlib.md5(now.isoformat().encode()).hexdigest()[:8], "domains": []}

    for domain in DOMAINS:
        readings = perceive(domain)
        reasoning = reason(readings)
        actions = act(reasoning)
        entry = {"domain": domain["name"], "perception": readings, "reasoning": reasoning, "actions": actions}
        log["domains"].append(entry)

    # Simulate refinement with past data
    log["refinement"] = refine(log["domains"])
    log["summary"] = {
        "total_domains": len(DOMAINS),
        "interventions": sum(1 for d in log["domains"] if d["reasoning"]["decision"] == "intervene"),
        "avg_risk": round(sum(d["reasoning"]["risk_score"] for d in log["domains"]) / len(DOMAINS), 4),
    }

    os.makedirs("logs", exist_ok=True)
    date_str = now.strftime("%Y-%m-%d")

    # JSON log
    with open(f"logs/{date_str}.json", "w") as f:
        json.dump(log, f, indent=2)

    # Markdown report
    md = [f"# Agent Improvement Report — {date_str}\n"]
    md.append(f"**Cycle ID:** `{log['cycle_id']}`\n")
    md.append(f"| Domain | Risk Score | Decision | Alerts |")
    md.append(f"|--------|-----------|----------|--------|")
    for d in log["domains"]:
        alerts = ", ".join(d["reasoning"]["alerts"]) or "none"
        md.append(f"| {d['domain']} | {d['reasoning']['risk_score']} | {d['reasoning']['decision']} | {alerts} |")
    md.append(f"\n**Summary:** {log['summary']['interventions']}/{log['summary']['total_domains']} domains required intervention. Average risk: {log['summary']['avg_risk']}")
    md.append(f"\n**Refinement:** {log['refinement']}")

    with open(f"logs/{date_str}.md", "w") as f:
        f.write("\n".join(md))

    print(f"[agent-improvement] Report generated: logs/{date_str}.md")

if __name__ == "__main__":
    main()
