"""
Claude Code Token Usage Calculator & HTML Report Generator
============================================================
Scans all Claude Code session JSONL files and calculates daily token usage.
Works with relay/proxy services where API-level token tracking is unavailable.

Usage:
    python claude_token_usage.py                          # Show last 30 days (console)
    python claude_token_usage.py --days 7                 # Show last 7 days
    python claude_token_usage.py --all                    # Show all time
    python claude_token_usage.py --date 2026-04-15        # Show specific date
    python claude_token_usage.py --csv output.csv         # Export to CSV
    python claude_token_usage.py --html report.html       # Generate HTML report
    python claude_token_usage.py --html report.html --all # HTML report with all data
"""

import json
import os
import sys
import argparse
import html as html_module
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Claude pricing (per million tokens) - update as needed
PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0, "cache_read": 1.50, "cache_write": 18.75},
    "claude-haiku-3.5": {"input": 0.80, "output": 4.0, "cache_read": 0.08, "cache_write": 1.0},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
    "claude-opus-4": {"input": 15.0, "output": 75.0, "cache_read": 1.50, "cache_write": 18.75},
    "default": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
}


def get_pricing(model_name: str) -> dict:
    if not model_name:
        return PRICING["default"]
    if model_name in PRICING:
        return PRICING[model_name]
    for key in PRICING:
        if model_name.startswith(key):
            return PRICING[key]
    model_lower = model_name.lower()
    if "opus" in model_lower:
        return PRICING["claude-opus-4"]
    elif "haiku" in model_lower:
        return PRICING["claude-haiku-3.5"]
    elif "sonnet" in model_lower:
        return PRICING["claude-sonnet-4"]
    return PRICING["default"]


def find_session_files(claude_dir: str) -> list:
    projects_dir = os.path.join(claude_dir, "projects")
    if not os.path.exists(projects_dir):
        print(f"Error: Projects directory not found at {projects_dir}")
        sys.exit(1)
    jsonl_files = []
    for root, dirs, files in os.walk(projects_dir):
        for f in files:
            if f.endswith(".jsonl"):
                jsonl_files.append(os.path.join(root, f))
    return jsonl_files


def parse_session_file(filepath: str) -> list:
    records = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") != "assistant":
                    continue
                message = entry.get("message", {})
                usage = message.get("usage", {})
                if not usage:
                    continue
                timestamp = entry.get("timestamp", "")
                model = message.get("model", "unknown")
                session_id = entry.get("sessionId", "")
                is_subagent = "/subagents/" in filepath or "\\subagents\\" in filepath
                cwd = entry.get("cwd", "")
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                cache_creation = usage.get("cache_creation_input_tokens", 0)
                cache_read = usage.get("cache_read_input_tokens", 0)
                cache_creation_obj = usage.get("cache_creation", {})
                if cache_creation_obj:
                    cache_creation += cache_creation_obj.get("ephemeral_1h_input_tokens", 0)
                    cache_creation += cache_creation_obj.get("ephemeral_5m_input_tokens", 0)
                records.append({
                    "timestamp": timestamp,
                    "model": model,
                    "session_id": session_id,
                    "is_subagent": is_subagent,
                    "cwd": cwd,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_creation_tokens": cache_creation,
                    "cache_read_tokens": cache_read,
                })
    except Exception:
        pass
    return records


def calculate_cost(record: dict) -> float:
    pricing = get_pricing(record["model"])
    cost = 0.0
    cost += record["input_tokens"] * pricing["input"] / 1_000_000
    cost += record["output_tokens"] * pricing["output"] / 1_000_000
    cost += record["cache_creation_tokens"] * pricing["cache_write"] / 1_000_000
    cost += record["cache_read_tokens"] * pricing["cache_read"] / 1_000_000
    return cost


def aggregate_daily(records: list) -> dict:
    daily = defaultdict(lambda: {
        "input_tokens": 0, "output_tokens": 0,
        "cache_creation_tokens": 0, "cache_read_tokens": 0,
        "total_tokens": 0, "api_calls": 0,
        "sessions": set(), "models": defaultdict(int), "cost_usd": 0.0,
    })
    for r in records:
        ts = r["timestamp"]
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            continue
        d = daily[date_str]
        d["input_tokens"] += r["input_tokens"]
        d["output_tokens"] += r["output_tokens"]
        d["cache_creation_tokens"] += r["cache_creation_tokens"]
        d["cache_read_tokens"] += r["cache_read_tokens"]
        d["total_tokens"] += r["input_tokens"] + r["output_tokens"] + r["cache_creation_tokens"] + r["cache_read_tokens"]
        d["api_calls"] += 1
        if r["session_id"]:
            d["sessions"].add(r["session_id"])
        d["models"][r["model"]] += 1
        d["cost_usd"] += calculate_cost(r)
    return daily


def aggregate_hourly(records: list, utc_offset: int = 8) -> dict:
    """Aggregate records by hour (0-23) in local timezone (default UTC+8 Beijing)."""
    hourly = defaultdict(lambda: {"api_calls": 0, "total_tokens": 0, "cost_usd": 0.0})
    offset = timedelta(hours=utc_offset)
    for r in records:
        ts = r["timestamp"]
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            local_dt = dt + offset
            hour = local_dt.hour
        except (ValueError, AttributeError):
            continue
        h = hourly[hour]
        h["api_calls"] += 1
        h["total_tokens"] += r["input_tokens"] + r["output_tokens"] + r["cache_creation_tokens"] + r["cache_read_tokens"]
        h["cost_usd"] += calculate_cost(r)
    return hourly


def aggregate_by_model(records: list) -> dict:
    """Aggregate records by model."""
    models = defaultdict(lambda: {
        "input_tokens": 0, "output_tokens": 0,
        "cache_creation_tokens": 0, "cache_read_tokens": 0,
        "total_tokens": 0, "api_calls": 0, "cost_usd": 0.0,
    })
    for r in records:
        m = models[r["model"]]
        m["input_tokens"] += r["input_tokens"]
        m["output_tokens"] += r["output_tokens"]
        m["cache_creation_tokens"] += r["cache_creation_tokens"]
        m["cache_read_tokens"] += r["cache_read_tokens"]
        m["total_tokens"] += r["input_tokens"] + r["output_tokens"] + r["cache_creation_tokens"] + r["cache_read_tokens"]
        m["api_calls"] += 1
        m["cost_usd"] += calculate_cost(r)
    return models


def format_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def filter_records_by_dates(records: list, sorted_dates: list) -> list:
    """Filter records to only include those within the sorted_dates range."""
    date_set = set(sorted_dates)
    filtered = []
    for r in records:
        ts = r["timestamp"]
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d")
            if date_str in date_set:
                filtered.append(r)
        except (ValueError, AttributeError):
            continue
    return filtered


def generate_html_report(daily: dict, sorted_dates: list, hourly: dict, model_data: dict, output_path: str, all_records_ref: list = None):
    """Generate a comprehensive HTML report with charts."""

    # --- Prepare data ---
    dates_json = json.dumps(sorted_dates)

    input_data = [daily[d]["input_tokens"] for d in sorted_dates]
    output_data = [daily[d]["output_tokens"] for d in sorted_dates]
    cache_w_data = [daily[d]["cache_creation_tokens"] for d in sorted_dates]
    cache_r_data = [daily[d]["cache_read_tokens"] for d in sorted_dates]
    cost_data = [round(daily[d]["cost_usd"], 2) for d in sorted_dates]
    calls_data = [daily[d]["api_calls"] for d in sorted_dates]
    sessions_data = [len(daily[d]["sessions"]) for d in sorted_dates]

    # 7-day moving average for cost
    ma7_cost = []
    for i in range(len(cost_data)):
        start = max(0, i - 6)
        window = cost_data[start:i + 1]
        ma7_cost.append(round(sum(window) / len(window), 2))

    # Totals
    total_input = sum(input_data)
    total_output = sum(output_data)
    total_cache_w = sum(cache_w_data)
    total_cache_r = sum(cache_r_data)
    total_tokens = total_input + total_output + total_cache_w + total_cache_r
    total_cost = sum(cost_data)
    total_calls = sum(calls_data)
    all_sessions = set()
    for d in sorted_dates:
        all_sessions.update(daily[d]["sessions"])
    total_sessions = len(all_sessions)
    num_days = len(sorted_dates)
    avg_daily_tokens = total_tokens / num_days if num_days else 0
    avg_daily_cost = total_cost / num_days if num_days else 0

    # Peak day
    peak_idx = cost_data.index(max(cost_data)) if cost_data else 0
    peak_date = sorted_dates[peak_idx] if sorted_dates else "N/A"
    peak_cost = cost_data[peak_idx] if cost_data else 0
    peak_tokens = (input_data[peak_idx] + output_data[peak_idx] + cache_w_data[peak_idx] + cache_r_data[peak_idx]) if sorted_dates else 0

    # Hourly data
    hourly_labels = [f"{h:02d}:00" for h in range(24)]
    hourly_calls = [hourly.get(h, {}).get("api_calls", 0) for h in range(24)]
    hourly_tokens = [hourly.get(h, {}).get("total_tokens", 0) for h in range(24)]
    peak_hour = hourly_calls.index(max(hourly_calls)) if hourly_calls else 0
    peak_hour_calls = max(hourly_calls) if hourly_calls else 0

    # Model data
    model_names = sorted(model_data.keys(), key=lambda x: -model_data[x]["total_tokens"])
    cache_total = total_cache_r + total_cache_w
    cache_rate = cache_total / total_tokens * 100 if total_tokens else 0
    input_pct = total_input / total_tokens * 100 if total_tokens else 0
    output_pct = total_output / total_tokens * 100 if total_tokens else 0
    cache_r_pct = total_cache_r / total_tokens * 100 if total_tokens else 0
    cache_w_pct = total_cache_w / total_tokens * 100 if total_tokens else 0
    io_ratio = total_input / total_output if total_output else 0
    avg_input_per_call = total_input / total_calls if total_calls else 0
    avg_output_per_call = total_output / total_calls if total_calls else 0
    avg_cache_per_call = total_cache_r / total_calls if total_calls else 0
    # Cost breakdown
    if all_records_ref:
        cost_from_input = sum(r["input_tokens"] * get_pricing(r["model"])["input"] / 1e6 for r in all_records_ref)
        cost_from_output = sum(r["output_tokens"] * get_pricing(r["model"])["output"] / 1e6 for r in all_records_ref)
        cost_from_cache_r = sum(r["cache_read_tokens"] * get_pricing(r["model"])["cache_read"] / 1e6 for r in all_records_ref)
    else:
        cost_from_input = cost_from_output = cost_from_cache_r = 0
    input_cost_pct = cost_from_input / total_cost * 100 if total_cost else 0
    output_cost_pct = cost_from_output / total_cost * 100 if total_cost else 0
    cache_r_cost_pct = cost_from_cache_r / total_cost * 100 if total_cost else 0
    # Cache health assessment
    if cache_rate >= 85:
        cache_health = "Excellent"
        cache_health_color = "#10b981"
        cache_health_note = "Cache hit rate is outstanding. The caching mechanism is working optimally, significantly reducing input costs."
    elif cache_rate >= 60:
        cache_health = "Good"
        cache_health_color = "#3b82f6"
        cache_health_note = "Cache hit rate is healthy. Most repeated context is being served from cache."
    elif cache_rate >= 30:
        cache_health = "Fair"
        cache_health_color = "#f59e0b"
        cache_health_note = "Cache hit rate is moderate. Consider longer sessions or fewer context switches to improve caching."
    else:
        cache_health = "Low"
        cache_health_color = "#ef4444"
        cache_health_note = "Cache hit rate is low. Short sessions or frequent context changes may be preventing effective caching."

    # Estimated savings from cache
    # If cache_read had been billed as regular input instead
    top_model = model_names[0] if model_names else "default"
    top_pricing = get_pricing(top_model)
    cache_savings = total_cache_r * (top_pricing["input"] - top_pricing["cache_read"]) / 1e6
    savings_pct = cache_savings / (total_cost + cache_savings) * 100 if (total_cost + cache_savings) else 0

    # Top model cost share
    top_model_cost = model_data[model_names[0]]["cost_usd"] if model_names else 0
    top_model_cost_pct = top_model_cost / total_cost * 100 if total_cost else 0
    top_model_display = model_names[0].replace("claude-", "").replace("-20250514", "") if model_names else "N/A"

    # Highest & lowest cost days
    lowest_idx = cost_data.index(min(cost_data)) if cost_data else 0
    lowest_date = sorted_dates[lowest_idx] if sorted_dates else "N/A"
    lowest_cost = cost_data[lowest_idx] if cost_data else 0
    cost_volatility = max(cost_data) / min(cost_data) if cost_data and min(cost_data) > 0 else 0

    model_calls_list = [model_data[m]["api_calls"] for m in model_names]
    model_tokens_list = [model_data[m]["total_tokens"] for m in model_names]
    model_cost_list = [round(model_data[m]["cost_usd"], 2) for m in model_names]
    # Simplify model names for display
    model_display_names = []
    for m in model_names:
        name = m.replace("claude-", "").replace("-20250514", "")
        model_display_names.append(name)

    # Weekday vs Weekend
    weekday_costs, weekend_costs = [], []
    weekday_tokens, weekend_tokens = [], []
    for d in sorted_dates:
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
            if dt.weekday() < 5:
                weekday_costs.append(daily[d]["cost_usd"])
                weekday_tokens.append(daily[d]["total_tokens"])
            else:
                weekend_costs.append(daily[d]["cost_usd"])
                weekend_tokens.append(daily[d]["total_tokens"])
        except ValueError:
            pass
    avg_weekday_cost = sum(weekday_costs) / len(weekday_costs) if weekday_costs else 0
    avg_weekend_cost = sum(weekend_costs) / len(weekend_costs) if weekend_costs else 0
    avg_weekday_tokens = sum(weekday_tokens) / len(weekday_tokens) if weekday_tokens else 0
    avg_weekend_tokens = sum(weekend_tokens) / len(weekend_tokens) if weekend_tokens else 0

    # --- Alerts & Attention Points ---
    alerts = []  # list of (level, icon, title, detail)  level: "critical", "warning", "info"

    # 1. Cost spike days: any day > 3x average (skip for single-day queries)
    if avg_daily_cost > 0 and num_days > 1:
        spike_days = [(d, daily[d]["cost_usd"]) for d in sorted_dates if daily[d]["cost_usd"] > avg_daily_cost * 3]
        if spike_days:
            spike_list = ", ".join(f"{d} (${c:,.0f})" for d, c in spike_days)
            alerts.append(("critical", "spike",
                f"{len(spike_days)} cost spike day(s) detected (&gt;3x daily average)",
                f"Days exceeding ${avg_daily_cost * 3:,.0f} threshold: {spike_list}. "
                f"These spikes often indicate heavy multi-agent parallel runs or large codebase operations. "
                f"Review whether all tasks required Opus-tier reasoning."))

    # 2. High Opus concentration — cost optimization opportunity
    if top_model_cost_pct > 90 and "opus" in (model_names[0] if model_names else "").lower():
        sonnet_calls = sum(model_data[m]["api_calls"] for m in model_names if "sonnet" in m.lower())
        opus_calls = sum(model_data[m]["api_calls"] for m in model_names if "opus" in m.lower())
        total_real = opus_calls + sonnet_calls
        sonnet_pct = sonnet_calls / total_real * 100 if total_real else 0
        potential_save = top_model_cost * 0.20 * (top_pricing["input"] - get_pricing("claude-sonnet-4")["input"]) / top_pricing["input"]
        alerts.append(("warning", "model",
            f"Opus dominates {top_model_cost_pct:.0f}% of cost — optimization opportunity",
            f"Only {sonnet_pct:.1f}% of calls use Sonnet. "
            f"Routing 20% of simpler tasks (search, formatting, boilerplate) to Sonnet could save ~${potential_save:,.0f}. "
            f"Opus input costs {top_pricing['input']/get_pricing('claude-sonnet-4')['input']:.0f}x more than Sonnet per token."))

    # 3. Cache health warning
    if cache_rate < 60:
        alerts.append(("warning", "cache",
            f"Cache hit rate is only {cache_rate:.1f}% — below healthy threshold",
            "A rate below 60% means most requests are paying full input price. "
            "Try longer sessions, avoid frequent /clear or context resets, "
            "and batch related tasks within the same session."))

    # 4. Output ratio anomaly — too low may mean excessive tool-use loops
    if output_pct < 0.3 and total_calls > 100:
        alerts.append(("info", "ratio",
            f"Output is only {output_pct:.2f}% of total tokens",
            "Extremely low output ratio suggests most API calls are tool-use chains with minimal text generation. "
            "This is normal for heavy coding sessions but worth noting for cost awareness — "
            "each tool call still consumes full input context."))

    # 5. High daily volatility (skip for single-day queries)
    if cost_volatility > 20 and num_days > 1:
        alerts.append(("warning", "volatility",
            f"Cost volatility is {cost_volatility:.0f}x between busiest and quietest days",
            f"The busiest day ({peak_date}, ${peak_cost:,.0f}) cost {cost_volatility:.0f}x more than the quietest "
            f"({lowest_date}, ${lowest_cost:,.0f}). High variance makes budget forecasting difficult. "
            "Consider setting daily spending alerts or session-level token budgets."))

    # 6. Large single-day percentage of total cost (skip for single-day queries)
    if peak_cost > 0 and total_cost > 0 and num_days > 1:
        peak_share = peak_cost / total_cost * 100
        if peak_share > 25:
            alerts.append(("warning", "concentration",
                f"Single day ({peak_date}) accounts for {peak_share:.0f}% of total cost",
                f"${peak_cost:,.0f} out of ${total_cost:,.0f} total was spent on {peak_date} alone. "
                "This level of concentration means a few heavy sessions dominate overall spending."))

    # 7. High average input per call (context bloat)
    if avg_input_per_call > 50000:
        alerts.append(("info", "context",
            f"Average input per call is {format_tokens(int(avg_input_per_call))} tokens",
            "Large average input suggests conversations with extensive context (system prompts, file contents, "
            "long histories). Consider using /compact more frequently or splitting tasks into smaller sessions "
            "to keep context lean."))

    # 8. Estimated monthly projection
    if num_days >= 7:
        projected_monthly = avg_daily_cost * 30
        if projected_monthly > 5000:
            level = "critical" if projected_monthly > 10000 else "warning"
            alerts.append((level, "projection",
                f"Projected monthly cost: ${projected_monthly:,.0f}",
                f"Based on the current {num_days}-day average of ${avg_daily_cost:,.0f}/day, "
                f"the 30-day projection is ${projected_monthly:,.0f}. "
                "Consider reviewing high-cost patterns and model selection to optimize spend."))

    # 9. Weekend usage spike (unusual if weekend >> weekday)
    if avg_weekend_cost > avg_weekday_cost * 1.5 and len(weekend_costs) >= 2:
        alerts.append(("info", "weekend",
            f"Weekend average (${avg_weekend_cost:,.0f}) exceeds weekday (${avg_weekday_cost:,.0f})",
            "Weekend usage is significantly higher than weekday, which is atypical. "
            "This may indicate batch processing jobs or unattended agent runs on weekends."))

    # Build alerts HTML
    alerts_html = ""
    if alerts:
        alerts_html = '<hr>\n<h3 style="color:var(--text-primary);font-size:1rem;margin-bottom:14px;">Alerts &amp; Attention Points</h3>\n'
        for level, icon, title, detail in alerts:
            if level == "critical":
                border_color = "var(--accent-red)"
                badge_bg = "var(--accent-red)"
                badge_text = "CRITICAL"
                icon_char = "&#9888;"  # ⚠
            elif level == "warning":
                border_color = "var(--accent-amber)"
                badge_bg = "var(--accent-amber)"
                badge_text = "WARNING"
                icon_char = "&#9888;"
            else:
                border_color = "var(--accent-cyan)"
                badge_bg = "var(--accent-cyan)"
                badge_text = "INFO"
                icon_char = "&#8505;"  # ℹ
            alerts_html += f"""<div class="alert-item" style="border-left-color:{border_color}">
    <div class="alert-header">
        <span class="alert-badge" style="background:{badge_bg}">{badge_text}</span>
        <span class="alert-title">{title}</span>
    </div>
    <div class="alert-detail">{detail}</div>
</div>\n"""

    # Daily table rows
    table_rows = ""
    for d in sorted_dates:
        dd = daily[d]
        top_model = max(dd["models"].items(), key=lambda x: x[1])[0] if dd["models"] else "N/A"
        top_model_short = top_model.replace("claude-", "").replace("-20250514", "")
        table_rows += f"""<tr>
            <td>{d}</td>
            <td class="num">{dd['input_tokens']:,}</td>
            <td class="num">{dd['output_tokens']:,}</td>
            <td class="num">{dd['cache_creation_tokens']:,}</td>
            <td class="num">{dd['cache_read_tokens']:,}</td>
            <td class="num total-col">{dd['total_tokens']:,}</td>
            <td class="num">{dd['api_calls']:,}</td>
            <td class="num">{len(dd['sessions'])}</td>
            <td class="num cost-col">${dd['cost_usd']:,.2f}</td>
            <td>{top_model_short}</td>
        </tr>\n"""

    # Model table rows
    model_table_rows = ""
    for m in model_names:
        md = model_data[m]
        pct_tokens = md["total_tokens"] / total_tokens * 100 if total_tokens else 0
        pct_calls = md["api_calls"] / total_calls * 100 if total_calls else 0
        display_name = m.replace("claude-", "").replace("-20250514", "")
        model_table_rows += f"""<tr>
            <td>{display_name}</td>
            <td class="num">{md['api_calls']:,}</td>
            <td class="num">{pct_calls:.1f}%</td>
            <td class="num">{md['total_tokens']:,}</td>
            <td class="num">{pct_tokens:.1f}%</td>
            <td class="num">{md['input_tokens']:,}</td>
            <td class="num">{md['output_tokens']:,}</td>
            <td class="num cost-col">${md['cost_usd']:,.2f}</td>
        </tr>\n"""

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Chart colors
    colors = [
        "rgba(99, 102, 241, 0.85)",   # indigo
        "rgba(16, 185, 129, 0.85)",   # emerald
        "rgba(245, 158, 11, 0.85)",   # amber
        "rgba(239, 68, 68, 0.85)",    # red
        "rgba(139, 92, 246, 0.85)",   # violet
        "rgba(6, 182, 212, 0.85)",    # cyan
        "rgba(236, 72, 153, 0.85)",   # pink
        "rgba(34, 197, 94, 0.85)",    # green
    ]
    chart_colors_json = json.dumps(colors)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Claude Code Token Usage Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
:root {{
    --bg-primary: #0f172a;
    --bg-secondary: #1e293b;
    --bg-card: #1e293b;
    --bg-card-hover: #334155;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --border: #334155;
    --accent-blue: #3b82f6;
    --accent-green: #10b981;
    --accent-amber: #f59e0b;
    --accent-red: #ef4444;
    --accent-purple: #8b5cf6;
    --accent-cyan: #06b6d4;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans SC', sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
    padding: 0;
}}
.container {{
    max-width: 1400px;
    margin: 0 auto;
    padding: 24px;
}}
header {{
    text-align: center;
    padding: 40px 0 20px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 32px;
}}
header h1 {{
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
}}
header .subtitle {{
    color: var(--text-secondary);
    font-size: 0.95rem;
}}
.section {{
    margin-bottom: 36px;
}}
.section-title {{
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 16px;
    padding-left: 12px;
    border-left: 3px solid var(--accent-blue);
}}
/* Summary Cards */
.cards {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
}}
.card {{
    background: var(--bg-card);
    border-radius: 12px;
    padding: 20px;
    border: 1px solid var(--border);
    transition: transform 0.2s, border-color 0.2s;
}}
.card:hover {{
    transform: translateY(-2px);
    border-color: var(--accent-blue);
}}
.card .label {{
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    margin-bottom: 6px;
}}
.card .value {{
    font-size: 1.6rem;
    font-weight: 700;
}}
.card .sub {{
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-top: 4px;
}}
.card.blue .value {{ color: var(--accent-blue); }}
.card.green .value {{ color: var(--accent-green); }}
.card.amber .value {{ color: var(--accent-amber); }}
.card.red .value {{ color: var(--accent-red); }}
.card.purple .value {{ color: var(--accent-purple); }}
.card.cyan .value {{ color: var(--accent-cyan); }}
/* Charts */
.chart-container {{
    background: var(--bg-card);
    border-radius: 12px;
    padding: 24px;
    border: 1px solid var(--border);
    margin-bottom: 24px;
}}
.chart-row {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
}}
@media (max-width: 900px) {{
    .chart-row {{ grid-template-columns: 1fr; }}
}}
.chart-wrap {{
    position: relative;
    width: 100%;
}}
.chart-wrap.tall {{ height: 400px; }}
.chart-wrap.medium {{ height: 320px; }}
/* Weekday/Weekend comparison */
.compare-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
}}
.compare-card {{
    background: var(--bg-card);
    border-radius: 12px;
    padding: 24px;
    border: 1px solid var(--border);
    text-align: center;
}}
.compare-card h3 {{
    font-size: 1rem;
    color: var(--text-secondary);
    margin-bottom: 16px;
}}
.compare-card .metric {{
    margin-bottom: 12px;
}}
.compare-card .metric .val {{
    font-size: 1.5rem;
    font-weight: 700;
}}
.compare-card .metric .lbl {{
    font-size: 0.8rem;
    color: var(--text-muted);
}}
/* Tables */
.table-container {{
    background: var(--bg-card);
    border-radius: 12px;
    border: 1px solid var(--border);
    overflow-x: auto;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
}}
thead th {{
    background: rgba(51, 65, 85, 0.6);
    padding: 12px 14px;
    text-align: left;
    font-weight: 600;
    color: var(--text-secondary);
    border-bottom: 2px solid var(--border);
    position: sticky;
    top: 0;
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
}}
thead th:hover {{
    color: var(--text-primary);
}}
thead th.sorted-asc::after {{ content: " \\25B2"; font-size: 0.7em; }}
thead th.sorted-desc::after {{ content: " \\25BC"; font-size: 0.7em; }}
tbody tr {{
    border-bottom: 1px solid var(--border);
    transition: background 0.15s;
}}
tbody tr:hover {{
    background: var(--bg-card-hover);
}}
td {{
    padding: 10px 14px;
    white-space: nowrap;
}}
td.num {{
    text-align: right;
    font-variant-numeric: tabular-nums;
    font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
}}
td.total-col {{ color: var(--accent-blue); font-weight: 600; }}
td.cost-col {{ color: var(--accent-green); font-weight: 600; }}
tfoot td {{
    padding: 12px 14px;
    font-weight: 700;
    background: rgba(51, 65, 85, 0.4);
    border-top: 2px solid var(--border);
}}
/* Footer */
footer {{
    text-align: center;
    padding: 24px 0;
    color: var(--text-muted);
    font-size: 0.8rem;
    border-top: 1px solid var(--border);
    margin-top: 40px;
}}
/* Peak badge */
.peak-badge {{
    display: inline-block;
    background: var(--accent-amber);
    color: #000;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 10px;
    margin-left: 8px;
    vertical-align: middle;
}}
/* Executive Analysis */
.analysis-box {{
    background: linear-gradient(135deg, rgba(30,41,59,0.95), rgba(15,23,42,0.95));
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent-blue);
    border-radius: 12px;
    padding: 28px 32px;
    margin-bottom: 32px;
    line-height: 1.8;
}}
.analysis-box h2 {{
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--accent-blue);
    margin-bottom: 16px;
    letter-spacing: 0.02em;
}}
.analysis-box p {{
    color: var(--text-secondary);
    font-size: 0.92rem;
    margin-bottom: 12px;
}}
.analysis-box .highlight {{
    color: var(--text-primary);
    font-weight: 600;
}}
.analysis-box .good {{ color: var(--accent-green); font-weight: 700; }}
.analysis-box .warn {{ color: var(--accent-amber); font-weight: 700; }}
.analysis-box .bad {{ color: var(--accent-red); font-weight: 700; }}
.analysis-box .blue {{ color: var(--accent-blue); font-weight: 600; }}
.analysis-box .purple {{ color: var(--accent-purple); font-weight: 600; }}
.analysis-box hr {{
    border: none;
    border-top: 1px solid var(--border);
    margin: 16px 0;
}}
.analysis-box .metric-row {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
    margin: 16px 0;
}}
.analysis-box .metric-item {{
    background: rgba(51,65,85,0.3);
    border-radius: 8px;
    padding: 12px 16px;
}}
.analysis-box .metric-item .ml {{
    font-size: 0.78rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}
.analysis-box .metric-item .mv {{
    font-size: 1.2rem;
    font-weight: 700;
    margin-top: 2px;
}}
/* Alert items */
.alert-item {{
    background: rgba(51,65,85,0.25);
    border-left: 3px solid var(--accent-amber);
    border-radius: 6px;
    padding: 14px 18px;
    margin-bottom: 10px;
}}
.alert-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
}}
.alert-badge {{
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    color: #000;
    padding: 2px 8px;
    border-radius: 3px;
    flex-shrink: 0;
}}
.alert-title {{
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text-primary);
}}
.alert-detail {{
    font-size: 0.82rem;
    color: var(--text-secondary);
    line-height: 1.6;
    padding-left: 2px;
}}
</style>
</head>
<body>
<div class="container">

<header>
    <h1>Claude Code Token Usage Report</h1>
    <p class="subtitle">
        {sorted_dates[0] if sorted_dates else 'N/A'} ~ {sorted_dates[-1] if sorted_dates else 'N/A'}
        &nbsp;&middot;&nbsp; {num_days} days &nbsp;&middot;&nbsp; Generated {generated_at}
    </p>
</header>

<!-- ==================== Executive Analysis ==================== -->
<div class="analysis-box">
    <h2>Executive Analysis</h2>

    <p>
        Over the past <span class="highlight">{num_days} days</span>
        ({sorted_dates[0] if sorted_dates else 'N/A'} to {sorted_dates[-1] if sorted_dates else 'N/A'}),
        a total of <span class="highlight">{format_tokens(total_tokens)} tokens</span> were consumed
        across <span class="highlight">{total_calls:,} API calls</span>
        in <span class="highlight">{total_sessions} sessions</span>,
        with an estimated total cost of <span class="highlight">${total_cost:,.2f}</span>.
        The daily average is <span class="blue">{format_tokens(int(avg_daily_tokens))} tokens</span>
        and <span class="blue">${avg_daily_cost:,.2f}</span> per day.
    </p>

    <div class="metric-row">
        <div class="metric-item">
            <div class="ml">Input Tokens</div>
            <div class="mv" style="color:var(--accent-blue)">{format_tokens(total_input)} <span style="font-size:0.75rem;color:var(--text-muted)">({input_pct:.1f}%)</span></div>
        </div>
        <div class="metric-item">
            <div class="ml">Output Tokens</div>
            <div class="mv" style="color:var(--accent-green)">{format_tokens(total_output)} <span style="font-size:0.75rem;color:var(--text-muted)">({output_pct:.1f}%)</span></div>
        </div>
        <div class="metric-item">
            <div class="ml">Cache Read</div>
            <div class="mv" style="color:var(--accent-purple)">{format_tokens(total_cache_r)} <span style="font-size:0.75rem;color:var(--text-muted)">({cache_r_pct:.1f}%)</span></div>
        </div>
        <div class="metric-item">
            <div class="ml">Cache Write</div>
            <div class="mv" style="color:var(--accent-amber)">{format_tokens(total_cache_w)} <span style="font-size:0.75rem;color:var(--text-muted)">({cache_w_pct:.1f}%)</span></div>
        </div>
    </div>
    <div class="metric-row">
        <div class="metric-item">
            <div class="ml">Daily Avg Tokens</div>
            <div class="mv" style="color:var(--accent-cyan)">{format_tokens(int(avg_daily_tokens))}</div>
        </div>
        <div class="metric-item">
            <div class="ml">Daily Avg Cost</div>
            <div class="mv" style="color:var(--accent-green)">${avg_daily_cost:,.2f}</div>
        </div>
        <div class="metric-item">
            <div class="ml">Daily Avg API Calls</div>
            <div class="mv" style="color:var(--accent-purple)">{total_calls // num_days if num_days else 0:,}</div>
        </div>
        <div class="metric-item">
            <div class="ml">Avg Input / Call</div>
            <div class="mv" style="color:var(--text-primary)">{format_tokens(int(avg_input_per_call))} <span style="font-size:0.75rem;color:var(--text-muted)">+ {format_tokens(int(avg_cache_per_call))} cache</span></div>
        </div>
    </div>

    <hr>

    <p>
        <strong>Cache Performance:</strong>
        Cache hit rate is <span style="color:{cache_health_color};font-weight:700">{cache_rate:.1f}%</span>
        &mdash; rated <span style="color:{cache_health_color};font-weight:700">{cache_health}</span>.
        {cache_health_note}
        Cache reads saved an estimated <span class="good">${cache_savings:,.0f}</span> compared to
        full-price input billing, a <span class="good">{savings_pct:.0f}% cost reduction</span>.
    </p>

    <hr>

    <p>
        <strong>Cost Breakdown:</strong>
        Input tokens account for <span class="highlight">{input_cost_pct:.1f}%</span> of total cost,
        output tokens account for <span class="highlight">{output_cost_pct:.1f}%</span>,
        and cache reads account for <span class="highlight">{cache_r_cost_pct:.1f}%</span>.
        The I/O ratio is <span class="blue">{io_ratio:.1f}:1</span> (input to output),
        with an average of <span class="blue">{format_tokens(int(avg_input_per_call))}</span> input
        and <span class="blue">{format_tokens(int(avg_output_per_call))}</span> output per API call.
    </p>

    <p>
        <strong>Model Usage:</strong>
        The primary model is <span class="highlight">{top_model_display}</span>,
        contributing <span class="highlight">{top_model_cost_pct:.1f}%</span> of total cost.
        The busiest day was <span class="highlight">{peak_date}</span>
        (${peak_cost:,.2f}, {format_tokens(peak_tokens)} tokens),
        while the quietest was <span class="highlight">{lowest_date}</span> (${lowest_cost:,.2f}).
        Daily cost varies by up to <span class="warn">{cost_volatility:.0f}x</span> between peak and trough.
    </p>

{alerts_html}
</div>

<!-- ==================== Summary Cards ==================== -->
<div class="section">
    <h2 class="section-title">Overview</h2>
    <div class="cards">
        <div class="card blue">
            <div class="label">Total Tokens</div>
            <div class="value">{format_tokens(total_tokens)}</div>
            <div class="sub">Input {format_tokens(total_input)} / Output {format_tokens(total_output)}</div>
        </div>
        <div class="card green">
            <div class="label">Total Cost (Est.)</div>
            <div class="value">${total_cost:,.2f}</div>
            <div class="sub">Avg ${avg_daily_cost:,.2f} / day</div>
        </div>
        <div class="card purple">
            <div class="label">API Calls</div>
            <div class="value">{total_calls:,}</div>
            <div class="sub">Avg {total_calls // num_days if num_days else 0:,} / day</div>
        </div>
        <div class="card cyan">
            <div class="label">Sessions</div>
            <div class="value">{total_sessions:,}</div>
            <div class="sub">Avg {format_tokens(int(avg_daily_tokens))} tokens/day</div>
        </div>
        <div class="card amber">
            <div class="label">Peak Day</div>
            <div class="value">${peak_cost:,.2f}</div>
            <div class="sub">{peak_date} &middot; {format_tokens(peak_tokens)} tokens</div>
        </div>
        <div class="card red">
            <div class="label">Peak Hour (Beijing)</div>
            <div class="value">{peak_hour:02d}:00</div>
            <div class="sub">{peak_hour_calls:,} API calls total</div>
        </div>
    </div>
</div>

<!-- ==================== Daily Token Stacked Bar ==================== -->
<div class="section">
    <h2 class="section-title">Daily Token Usage</h2>
    <div class="chart-container">
        <div class="chart-wrap tall">
            <canvas id="dailyTokenChart"></canvas>
        </div>
    </div>
</div>

<!-- ==================== Cost Trend ==================== -->
<div class="section">
    <h2 class="section-title">Daily Cost Trend</h2>
    <div class="chart-container">
        <div class="chart-wrap tall">
            <canvas id="costChart"></canvas>
        </div>
    </div>
</div>

<!-- ==================== Model Distribution ==================== -->
<div class="section">
    <h2 class="section-title">Model Distribution</h2>
    <div class="chart-row">
        <div class="chart-container">
            <h3 style="color:var(--text-secondary);font-size:0.9rem;margin-bottom:12px;">By API Calls</h3>
            <div class="chart-wrap medium">
                <canvas id="modelCallsChart"></canvas>
            </div>
        </div>
        <div class="chart-container">
            <h3 style="color:var(--text-secondary);font-size:0.9rem;margin-bottom:12px;">By Token Usage</h3>
            <div class="chart-wrap medium">
                <canvas id="modelTokensChart"></canvas>
            </div>
        </div>
    </div>
    <div class="table-container" style="margin-top:16px;">
        <table>
            <thead><tr>
                <th>Model</th><th>API Calls</th><th>Calls %</th>
                <th>Total Tokens</th><th>Tokens %</th>
                <th>Input Tokens</th><th>Output Tokens</th><th>Cost (Est.)</th>
            </tr></thead>
            <tbody>{model_table_rows}</tbody>
        </table>
    </div>
</div>

<!-- ==================== Hourly Distribution ==================== -->
<div class="section">
    <h2 class="section-title">Hourly Activity Distribution (Beijing UTC+8) <span class="peak-badge">Peak: {peak_hour:02d}:00</span></h2>
    <div class="chart-container">
        <div class="chart-wrap medium">
            <canvas id="hourlyChart"></canvas>
        </div>
    </div>
</div>

<!-- ==================== Weekday vs Weekend ==================== -->
<div class="section">
    <h2 class="section-title">Weekday vs Weekend</h2>
    <div class="compare-grid">
        <div class="compare-card">
            <h3>Weekday (Mon-Fri)</h3>
            <div class="metric">
                <div class="val" style="color:var(--accent-blue)">{format_tokens(int(avg_weekday_tokens))}</div>
                <div class="lbl">Avg Daily Tokens</div>
            </div>
            <div class="metric">
                <div class="val" style="color:var(--accent-green)">${avg_weekday_cost:,.2f}</div>
                <div class="lbl">Avg Daily Cost</div>
            </div>
            <div class="metric">
                <div class="val" style="color:var(--text-secondary)">{len(weekday_costs)} days</div>
                <div class="lbl">Total Days</div>
            </div>
        </div>
        <div class="compare-card">
            <h3>Weekend (Sat-Sun)</h3>
            <div class="metric">
                <div class="val" style="color:var(--accent-blue)">{format_tokens(int(avg_weekend_tokens))}</div>
                <div class="lbl">Avg Daily Tokens</div>
            </div>
            <div class="metric">
                <div class="val" style="color:var(--accent-green)">${avg_weekend_cost:,.2f}</div>
                <div class="lbl">Avg Daily Cost</div>
            </div>
            <div class="metric">
                <div class="val" style="color:var(--text-secondary)">{len(weekend_costs)} days</div>
                <div class="lbl">Total Days</div>
            </div>
        </div>
    </div>
</div>

<!-- ==================== Daily Detail Table ==================== -->
<div class="section">
    <h2 class="section-title">Daily Detail</h2>
    <div class="table-container">
        <table id="dailyTable">
            <thead><tr>
                <th onclick="sortTable(0)">Date</th>
                <th onclick="sortTable(1)">Input</th>
                <th onclick="sortTable(2)">Output</th>
                <th onclick="sortTable(3)">Cache Write</th>
                <th onclick="sortTable(4)">Cache Read</th>
                <th onclick="sortTable(5)">Total</th>
                <th onclick="sortTable(6)">Calls</th>
                <th onclick="sortTable(7)">Sessions</th>
                <th onclick="sortTable(8)">Cost (Est.)</th>
                <th onclick="sortTable(9)">Top Model</th>
            </tr></thead>
            <tbody>{table_rows}</tbody>
            <tfoot><tr>
                <td>TOTAL</td>
                <td class="num">{total_input:,}</td>
                <td class="num">{total_output:,}</td>
                <td class="num">{total_cache_w:,}</td>
                <td class="num">{total_cache_r:,}</td>
                <td class="num total-col">{total_tokens:,}</td>
                <td class="num">{total_calls:,}</td>
                <td class="num">{total_sessions}</td>
                <td class="num cost-col">${total_cost:,.2f}</td>
                <td>-</td>
            </tr></tfoot>
        </table>
    </div>
</div>

<footer>
    Claude Code Token Usage Report &middot; Data from ~/.claude/projects/ session files &middot; Costs are estimates based on Anthropic official pricing
</footer>

</div><!-- /container -->

<script>
// ---------- Chart.js global defaults ----------
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = 'rgba(51,65,85,0.5)';
Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";

const chartColors = {chart_colors_json};

function fmtTokens(n) {{
    if (n >= 1e9) return (n/1e9).toFixed(1) + 'B';
    if (n >= 1e6) return (n/1e6).toFixed(1) + 'M';
    if (n >= 1e3) return (n/1e3).toFixed(1) + 'K';
    return n.toString();
}}

// ---------- 1. Daily Token Stacked Bar ----------
new Chart(document.getElementById('dailyTokenChart'), {{
    type: 'bar',
    data: {{
        labels: {dates_json},
        datasets: [
            {{ label: 'Input', data: {json.dumps(input_data)}, backgroundColor: 'rgba(99,102,241,0.8)' }},
            {{ label: 'Output', data: {json.dumps(output_data)}, backgroundColor: 'rgba(16,185,129,0.8)' }},
            {{ label: 'Cache Write', data: {json.dumps(cache_w_data)}, backgroundColor: 'rgba(245,158,11,0.8)' }},
            {{ label: 'Cache Read', data: {json.dumps(cache_r_data)}, backgroundColor: 'rgba(139,92,246,0.8)' }}
        ]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            tooltip: {{
                mode: 'index',
                callbacks: {{
                    label: ctx => ctx.dataset.label + ': ' + fmtTokens(ctx.parsed.y),
                    footer: items => 'Total: ' + fmtTokens(items.reduce((s,i) => s + i.parsed.y, 0))
                }}
            }},
            legend: {{ position: 'top' }}
        }},
        scales: {{
            x: {{ stacked: true, ticks: {{ maxRotation: 45 }} }},
            y: {{
                stacked: true,
                ticks: {{ callback: v => fmtTokens(v) }}
            }}
        }}
    }}
}});

// ---------- 2. Cost Trend ----------
new Chart(document.getElementById('costChart'), {{
    type: 'line',
    data: {{
        labels: {dates_json},
        datasets: [
            {{
                label: 'Daily Cost ($)',
                data: {json.dumps(cost_data)},
                borderColor: 'rgba(16,185,129,1)',
                backgroundColor: 'rgba(16,185,129,0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 4,
                pointHoverRadius: 7
            }},
            {{
                label: '7-Day Moving Avg ($)',
                data: {json.dumps(ma7_cost)},
                borderColor: 'rgba(245,158,11,0.9)',
                borderDash: [6, 3],
                fill: false,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 4
            }}
        ]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            tooltip: {{
                mode: 'index',
                intersect: false,
                callbacks: {{
                    label: ctx => ctx.dataset.label + ': $' + ctx.parsed.y.toFixed(2)
                }}
            }}
        }},
        scales: {{
            y: {{
                ticks: {{ callback: v => '$' + v.toFixed(0) }}
            }},
            x: {{ ticks: {{ maxRotation: 45 }} }}
        }}
    }}
}});

// ---------- 3. Model Doughnut Charts ----------
new Chart(document.getElementById('modelCallsChart'), {{
    type: 'doughnut',
    data: {{
        labels: {json.dumps(model_display_names)},
        datasets: [{{ data: {json.dumps(model_calls_list)}, backgroundColor: chartColors.slice(0, {len(model_names)}) }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            tooltip: {{ callbacks: {{ label: ctx => ctx.label + ': ' + ctx.parsed.toLocaleString() + ' calls' }} }},
            legend: {{ position: 'bottom', labels: {{ padding: 16 }} }}
        }}
    }}
}});

new Chart(document.getElementById('modelTokensChart'), {{
    type: 'doughnut',
    data: {{
        labels: {json.dumps(model_display_names)},
        datasets: [{{ data: {json.dumps(model_tokens_list)}, backgroundColor: chartColors.slice(0, {len(model_names)}) }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            tooltip: {{ callbacks: {{ label: ctx => ctx.label + ': ' + fmtTokens(ctx.parsed) }} }},
            legend: {{ position: 'bottom', labels: {{ padding: 16 }} }}
        }}
    }}
}});

// ---------- 4. Hourly Activity ----------
const hourlyData = {json.dumps(hourly_calls)};
const peakH = {peak_hour};
const hourlyBgColors = hourlyData.map((v, i) => i === peakH ? 'rgba(245,158,11,0.9)' : 'rgba(99,102,241,0.7)');

new Chart(document.getElementById('hourlyChart'), {{
    type: 'bar',
    data: {{
        labels: {json.dumps(hourly_labels)},
        datasets: [{{
            label: 'API Calls',
            data: hourlyData,
            backgroundColor: hourlyBgColors,
            borderRadius: 4
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            tooltip: {{
                callbacks: {{
                    afterLabel: function(ctx) {{
                        const tokens = {json.dumps(hourly_tokens)};
                        return 'Tokens: ' + fmtTokens(tokens[ctx.dataIndex]);
                    }}
                }}
            }},
            legend: {{ display: false }}
        }},
        scales: {{
            y: {{ ticks: {{ callback: v => v.toLocaleString() }} }}
        }}
    }}
}});

// ---------- Table Sorting ----------
let sortCol = -1, sortAsc = true;
function sortTable(col) {{
    const table = document.getElementById('dailyTable');
    const tbody = table.tBodies[0];
    const rows = Array.from(tbody.rows);
    const headers = table.tHead.rows[0].cells;

    // Toggle direction
    if (sortCol === col) {{ sortAsc = !sortAsc; }}
    else {{ sortCol = col; sortAsc = true; }}

    // Update header classes
    for (let h of headers) {{ h.classList.remove('sorted-asc', 'sorted-desc'); }}
    headers[col].classList.add(sortAsc ? 'sorted-asc' : 'sorted-desc');

    rows.sort((a, b) => {{
        let va = a.cells[col].textContent.trim();
        let vb = b.cells[col].textContent.trim();
        // Try numeric (remove $, commas, %)
        const na = parseFloat(va.replace(/[$,%]/g, '').replace(/,/g, ''));
        const nb = parseFloat(vb.replace(/[$,%]/g, '').replace(/,/g, ''));
        if (!isNaN(na) && !isNaN(nb)) {{
            return sortAsc ? na - nb : nb - na;
        }}
        return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
    }});

    for (const r of rows) tbody.appendChild(r);
}}
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML report generated: {output_path}")


# ========== Console output (unchanged) ==========

def print_console_report(daily, sorted_dates):
    print("=" * 120)
    print(f"{'Date':<12} {'Input':>10} {'Output':>10} {'CacheWrite':>10} {'CacheRead':>10} {'Total':>10} {'Calls':>6} {'Sessions':>8} {'Cost($)':>10} {'Models'}")
    print("-" * 120)
    total_input = total_output = total_cache_w = total_cache_r = total_all = total_calls = 0
    total_cost = 0.0
    all_sessions = set()
    for date in sorted_dates:
        d = daily[date]
        models_str = ", ".join(f"{m}({c})" for m, c in sorted(d["models"].items(), key=lambda x: -x[1])[:3])
        print(f"{date:<12} {format_tokens(d['input_tokens']):>10} {format_tokens(d['output_tokens']):>10} "
              f"{format_tokens(d['cache_creation_tokens']):>10} {format_tokens(d['cache_read_tokens']):>10} "
              f"{format_tokens(d['total_tokens']):>10} {d['api_calls']:>6} {len(d['sessions']):>8} "
              f"${d['cost_usd']:>9.4f} {models_str}")
        total_input += d["input_tokens"]
        total_output += d["output_tokens"]
        total_cache_w += d["cache_creation_tokens"]
        total_cache_r += d["cache_read_tokens"]
        total_all += d["total_tokens"]
        total_calls += d["api_calls"]
        total_cost += d["cost_usd"]
        all_sessions.update(d["sessions"])
    print("-" * 120)
    print(f"{'TOTAL':<12} {format_tokens(total_input):>10} {format_tokens(total_output):>10} "
          f"{format_tokens(total_cache_w):>10} {format_tokens(total_cache_r):>10} "
          f"{format_tokens(total_all):>10} {total_calls:>6} {len(all_sessions):>8} "
          f"${total_cost:>9.4f}")
    print("=" * 120)
    if sorted_dates:
        avg_daily_cost = total_cost / len(sorted_dates)
        avg_daily_tokens = total_all / len(sorted_dates)
        print(f"\nAverage daily: {format_tokens(int(avg_daily_tokens))} tokens, ${avg_daily_cost:.4f}")
        print(f"Date range: {sorted_dates[0]} to {sorted_dates[-1]} ({len(sorted_dates)} days)")


def main():
    parser = argparse.ArgumentParser(description="Calculate daily Claude Code token usage")
    parser.add_argument("--days", type=int, default=30, help="Number of days to show (default: 30)")
    parser.add_argument("--all", action="store_true", help="Show all time data")
    parser.add_argument("--date", type=str, help="Show specific date (YYYY-MM-DD)")
    parser.add_argument("--csv", type=str, help="Export to CSV file")
    parser.add_argument("--html", type=str, nargs="?", const="auto", help="Generate HTML report (default filename: token-report-YYYY-MM-DD.html)")
    parser.add_argument("--claude-dir", type=str, default=None, help="Path to .claude directory")
    args = parser.parse_args()

    claude_dir = args.claude_dir or os.path.join(os.path.expanduser("~"), ".claude")
    print(f"Scanning Claude Code sessions in: {claude_dir}")
    print()

    session_files = find_session_files(claude_dir)
    print(f"Found {len(session_files)} session files")

    all_records = []
    for sf in session_files:
        records = parse_session_file(sf)
        all_records.extend(records)
    print(f"Parsed {len(all_records)} API call records")
    print()

    if not all_records:
        print("No token usage data found.")
        return

    daily = aggregate_daily(all_records)

    # Filter dates
    sorted_dates = sorted(daily.keys())
    if args.date:
        sorted_dates = [d for d in sorted_dates if d == args.date]
        if not sorted_dates:
            print(f"No data found for {args.date}")
            return
    elif not args.all:
        cutoff = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        sorted_dates = [d for d in sorted_dates if d >= cutoff]

    # CSV export
    if args.csv:
        with open(args.csv, "w", encoding="utf-8") as f:
            f.write("date,input_tokens,output_tokens,cache_write_tokens,cache_read_tokens,total_tokens,api_calls,sessions,cost_usd\n")
            for date in sorted_dates:
                d = daily[date]
                f.write(f"{date},{d['input_tokens']},{d['output_tokens']},{d['cache_creation_tokens']},{d['cache_read_tokens']},{d['total_tokens']},{d['api_calls']},{len(d['sessions'])},{d['cost_usd']:.4f}\n")
        print(f"Exported to {args.csv}")
        return

    # HTML report
    if args.html:
        if args.html == "auto":
            today_str = datetime.now().strftime("%Y-%m-%d")
            args.html = f"token-report-{today_str}.html"
        filtered_records = filter_records_by_dates(all_records, sorted_dates)
        hourly = aggregate_hourly(filtered_records)
        model_data = aggregate_by_model(filtered_records)
        generate_html_report(daily, sorted_dates, hourly, model_data, args.html, all_records_ref=filtered_records)
        return

    # Console output
    print_console_report(daily, sorted_dates)


if __name__ == "__main__":
    main()
