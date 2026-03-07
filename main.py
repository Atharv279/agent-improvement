#!/usr/bin/env python3
"""Agent Improvement Loop — Perceive, Reason, Act, Refine with visual analytics."""
import json, os, random, hashlib, datetime, glob
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

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
    vals = [v for v in readings.values() if isinstance(v, float)]
    risk = round(sum(vals) / max(len(vals), 1), 4)
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

def load_yesterday(date_str):
    yesterday = (datetime.datetime.strptime(date_str, "%Y-%m-%d") - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    path = f"logs/{yesterday}.json"
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None

def compute_delta(today_data, yesterday_data):
    if not yesterday_data:
        return {"status": "no_previous_data", "deltas": {}}
    deltas = {}
    today_risks = {d["domain"]: d["reasoning"]["risk_score"] for d in today_data["domains"]}
    yest_risks = {d["domain"]: d["reasoning"]["risk_score"] for d in yesterday_data.get("domains", [])}
    for domain, risk in today_risks.items():
        prev = yest_risks.get(domain)
        if prev is not None:
            change = round(((risk - prev) / max(prev, 0.001)) * 100, 1)
            deltas[domain] = {"today": risk, "yesterday": prev, "change_pct": change,
                              "direction": "up" if change > 0 else "down" if change < 0 else "flat"}
    return {"status": "compared", "deltas": deltas}

def generate_chart(log, date_str):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle(f"Agent Improvement Dashboard — {date_str}", fontsize=14, fontweight="bold")

    # 1: Risk scores per domain
    domains = [d["domain"] for d in log["domains"]]
    risks = [d["reasoning"]["risk_score"] for d in log["domains"]]
    colors = ["#e74c3c" if r > 0.6 else "#f39c12" if r > 0.4 else "#2ecc71" for r in risks]
    axes[0].barh(domains, risks, color=colors)
    axes[0].axvline(x=0.6, color="#e74c3c", linestyle="--", alpha=0.7, label="Intervention threshold")
    axes[0].set_xlim(0, 1)
    axes[0].set_xlabel("Risk Score")
    axes[0].set_title("Risk by Domain")
    axes[0].legend(fontsize=8)

    # 2: Alert distribution
    alert_counts = {}
    for d in log["domains"]:
        for a in d["reasoning"]["alerts"]:
            alert_counts[a] = alert_counts.get(a, 0) + 1
    if alert_counts:
        axes[1].pie(alert_counts.values(), labels=alert_counts.keys(), autopct="%1.0f%%",
                     colors=plt.cm.Set3.colors[:len(alert_counts)])
    else:
        axes[1].text(0.5, 0.5, "No Alerts", ha="center", va="center", fontsize=14)
    axes[1].set_title("Alert Distribution")

    # 3: Decision breakdown
    decisions = {}
    for d in log["domains"]:
        dec = d["reasoning"]["decision"]
        decisions[dec] = decisions.get(dec, 0) + 1
    dec_colors = {"intervene": "#e74c3c", "monitor": "#2ecc71"}
    axes[2].bar(decisions.keys(), decisions.values(), color=[dec_colors.get(k, "#3498db") for k in decisions.keys()])
    axes[2].set_ylabel("Count")
    axes[2].set_title("Decision Breakdown")

    plt.tight_layout()
    chart_path = f"logs/{date_str}_dashboard.png"
    plt.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close()

    # Historical trend chart
    history_files = sorted(glob.glob("logs/*.json"))[-14:]
    if len(history_files) >= 2:
        fig2, ax2 = plt.subplots(figsize=(12, 4))
        dates, avg_risks, interventions = [], [], []
        for hf in history_files:
            with open(hf) as f:
                h = json.load(f)
            d = os.path.basename(hf).replace(".json", "")
            dates.append(d)
            avg_risks.append(h.get("summary", {}).get("avg_risk", 0))
            interventions.append(h.get("summary", {}).get("interventions", 0))
        ax2.plot(dates, avg_risks, "o-", color="#e74c3c", label="Avg Risk", linewidth=2)
        ax2_twin = ax2.twinx()
        ax2_twin.bar(dates, interventions, alpha=0.3, color="#3498db", label="Interventions")
        ax2.set_ylabel("Average Risk Score")
        ax2_twin.set_ylabel("Interventions")
        ax2.set_title("14-Day Risk Trend")
        ax2.tick_params(axis="x", rotation=45)
        lines1, labels1 = ax2.get_legend_handles_labels()
        lines2, labels2 = ax2_twin.get_legend_handles_labels()
        ax2.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)
        plt.tight_layout()
        plt.savefig(f"logs/{date_str}_trend.png", dpi=150, bbox_inches="tight")
        plt.close()

    return chart_path

def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    log = {"timestamp": now.isoformat(), "cycle_id": hashlib.md5(now.isoformat().encode()).hexdigest()[:8], "domains": []}

    for domain in DOMAINS:
        readings = perceive(domain)
        reasoning = reason(readings)
        actions = act(reasoning)
        log["domains"].append({"domain": domain["name"], "perception": readings, "reasoning": reasoning, "actions": actions})

    log["refinement"] = refine(log["domains"])
    log["summary"] = {
        "total_domains": len(DOMAINS),
        "interventions": sum(1 for d in log["domains"] if d["reasoning"]["decision"] == "intervene"),
        "avg_risk": round(sum(d["reasoning"]["risk_score"] for d in log["domains"]) / len(DOMAINS), 4),
    }

    yesterday = load_yesterday(date_str)
    log["delta"] = compute_delta(log, yesterday)

    os.makedirs("logs", exist_ok=True)
    with open(f"logs/{date_str}.json", "w") as f:
        json.dump(log, f, indent=2)

    chart_path = generate_chart(log, date_str)

    md = [f"# Agent Improvement Report — {date_str}\n"]
    md.append(f"**Cycle ID:** `{log['cycle_id']}` | **Avg Risk:** {log['summary']['avg_risk']} | **Interventions:** {log['summary']['interventions']}/{log['summary']['total_domains']}\n")
    md.append(f"![Dashboard]({os.path.basename(chart_path)})\n")
    if os.path.exists(f"logs/{date_str}_trend.png"):
        md.append(f"![Trend]({date_str}_trend.png)\n")
    md.append(f"## Risk Matrix\n")
    md.append(f"| Domain | Risk Score | Decision | Alerts |")
    md.append(f"|--------|-----------|----------|--------|")
    for d in log["domains"]:
        alerts = ", ".join(d["reasoning"]["alerts"]) or "none"
        md.append(f"| {d['domain']} | {d['reasoning']['risk_score']} | {d['reasoning']['decision']} | {alerts} |")
    if log["delta"]["status"] == "compared":
        md.append(f"\n## Delta vs Yesterday\n")
        md.append(f"| Domain | Today | Yesterday | Change |")
        md.append(f"|--------|-------|-----------|--------|")
        for domain, delta in log["delta"]["deltas"].items():
            arrow = "📈" if delta["change_pct"] > 0 else "📉" if delta["change_pct"] < 0 else "➡️"
            md.append(f"| {domain} | {delta['today']} | {delta['yesterday']} | {arrow} {delta['change_pct']}% |")
    md.append(f"\n**Refinement:** `{log['refinement']}`")

    with open(f"logs/{date_str}.md", "w") as f:
        f.write("\n".join(md))
    print(f"[agent-improvement] v2.0 report + charts generated")

if __name__ == "__main__":
    main()
