"""
HealthOS — Trend Engine  (model/trend_engine.py)
=================================================
Analyzes 7-day session logs to surface real behavioral patterns,
correlations, and anomalies.  Output is injected into the AI prompt
so it can reference actual user history instead of guessing.

Detected patterns:
  - Sustained decline / improvement (energy/mood trending down or up)
  - Day-of-week patterns ("energy always low on Mondays")
  - Sleep-energy correlation ("your energy drops when you sleep <6h")
  - Sleep-mood correlation
  - Stress-energy correlation
  - Streak tracking (consecutive poor nights, low mood runs)
  - Recovery signals (improving after a bad streak)
  - Critical alerts (e.g. 5+ consecutive days of low mood)

Public API:
  analyze_trends(logs: list) -> TrendReport
  format_trend_block(report: TrendReport) -> str   # AI-ready text block
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

_MOOD_SCORE = {"low": 1, "neutral": 2, "good": 3}
_DOW_NAMES  = ["Monday", "Tuesday", "Wednesday", "Thursday",
               "Friday", "Saturday", "Sunday"]


def _mood_to_int(mood: str) -> Optional[int]:
    return _MOOD_SCORE.get((mood or "").lower())


def _to_float(val) -> Optional[float]:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _dow(date_str: str) -> Optional[str]:
    """'2026-02-24' → 'Monday'"""
    try:
        return _DOW_NAMES[datetime.strptime(date_str, "%Y-%m-%d").weekday()]
    except Exception:
        return None


def _trend_slope(values: list[float]) -> float:
    """
    Simple linear regression slope over index positions.
    Positive = improving, negative = declining.
    Returns 0.0 if fewer than 2 points.
    """
    n = len(values)
    if n < 2:
        return 0.0
    xs = list(range(n))
    x_mean = statistics.mean(xs)
    y_mean = statistics.mean(values)
    num    = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values))
    den    = sum((x - x_mean) ** 2 for x in xs)
    return num / den if den else 0.0


def _pearson(xs: list[float], ys: list[float]) -> Optional[float]:
    """Pearson correlation coefficient. Returns None if not enough data."""
    if len(xs) < 3:
        return None
    try:
        x_mean = statistics.mean(xs)
        y_mean = statistics.mean(ys)
        num    = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
        den_x  = sum((x - x_mean) ** 2 for x in xs) ** 0.5
        den_y  = sum((y - y_mean) ** 2 for y in ys) ** 0.5
        if den_x == 0 or den_y == 0:
            return None
        return round(num / (den_x * den_y), 2)
    except Exception:
        return None


# ──────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────

@dataclass
class TrendReport:
    """
    Full trend analysis result for one user's recent logs.
    Every field is optional — only populated when there is real evidence.
    """
    days_logged:     int   = 0

    # Trend directions  ("improving" | "declining" | "stable")
    energy_trend:    str   = "stable"
    mood_trend:      str   = "stable"
    sleep_trend:     str   = "stable"

    # Averages
    avg_energy:      Optional[float] = None
    avg_mood_score:  Optional[float] = None   # 1=low, 2=neutral, 3=good
    avg_sleep_hours: Optional[float] = None

    # Day-of-week weakest days
    low_energy_days: list[str] = field(default_factory=list)   # e.g. ["Monday","Tuesday"]
    low_mood_days:   list[str] = field(default_factory=list)
    poor_sleep_days: list[str] = field(default_factory=list)

    # Correlations  (float -1..1 or None)
    sleep_energy_corr: Optional[float] = None   # positive = more sleep → more energy
    sleep_mood_corr:   Optional[float] = None
    stress_energy_corr: Optional[float] = None  # negative = more stress → less energy

    # Streaks
    consecutive_low_energy: int = 0   # days in a row with energy ≤ 4
    consecutive_low_mood:   int = 0   # days in a row with mood == "low"
    consecutive_poor_sleep: int = 0   # days in a row with sleep ≤ 5h

    # Anomalies / highlights
    best_day:   Optional[str] = None   # date with highest combined score
    worst_day:  Optional[str] = None   # date with lowest combined score
    recovering: bool          = False  # last 2 days better than previous 2

    # Critical flags (severity 1 alerts)
    critical_alerts: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────
# CORE ANALYSIS
# ──────────────────────────────────────────────

def analyze_trends(logs: list) -> TrendReport:
    """
    Run the full trend analysis pipeline on a list of session logs.

    logs: newest-first list (as returned by session_memory.load_recent_logs)
          each entry: {"date", "energy", "mood", "sleep_hours", ...}

    Returns a TrendReport.
    """
    report = TrendReport()
    if not logs:
        return report

    # Reverse to chronological order for slope calculations
    chron = list(reversed(logs))
    report.days_logged = len(chron)

    # ── Extract series ─────────────────────────────────────────
    energy_series: list[tuple[str, float]] = []   # (date, value)
    mood_series:   list[tuple[str, int]]   = []
    sleep_series:  list[tuple[str, float]] = []
    stress_series: list[tuple[str, float]] = []

    for entry in chron:
        date = entry.get("date", "")
        e    = _to_float(entry.get("energy"))
        m    = _mood_to_int(entry.get("mood", ""))
        s    = _to_float(entry.get("sleep_hours"))
        st   = _to_float(entry.get("stress"))

        if e is not None:  energy_series.append((date, e))
        if m is not None:  mood_series.append((date, m))
        if s is not None:  sleep_series.append((date, s))
        if st is not None: stress_series.append((date, st))

    # ── Averages ───────────────────────────────────────────────
    if energy_series:
        report.avg_energy = round(statistics.mean(v for _, v in energy_series), 1)
    if mood_series:
        report.avg_mood_score = round(statistics.mean(v for _, v in mood_series), 2)
    if sleep_series:
        report.avg_sleep_hours = round(statistics.mean(v for _, v in sleep_series), 1)

    # ── Trend slopes ───────────────────────────────────────────
    if len(energy_series) >= 3:
        slope = _trend_slope([v for _, v in energy_series])
        if   slope >  0.3: report.energy_trend = "improving"
        elif slope < -0.3: report.energy_trend = "declining"

    if len(mood_series) >= 3:
        slope = _trend_slope([float(v) for _, v in mood_series])
        if   slope >  0.2: report.mood_trend = "improving"
        elif slope < -0.2: report.mood_trend = "declining"

    if len(sleep_series) >= 3:
        slope = _trend_slope([v for _, v in sleep_series])
        if   slope >  0.3: report.sleep_trend = "improving"
        elif slope < -0.3: report.sleep_trend = "declining"

    # ── Day-of-week patterns ───────────────────────────────────
    dow_energy: dict[str, list[float]] = {}
    dow_mood:   dict[str, list[float]] = {}
    dow_sleep:  dict[str, list[float]] = {}

    for date, v in energy_series:
        day = _dow(date)
        if day: dow_energy.setdefault(day, []).append(v)
    for date, v in mood_series:
        day = _dow(date)
        if day: dow_mood.setdefault(day, []).append(float(v))
    for date, v in sleep_series:
        day = _dow(date)
        if day: dow_sleep.setdefault(day, []).append(v)

    if dow_energy:
        avg_e     = statistics.mean(v for _, v in energy_series)
        threshold = avg_e - 1.5
        report.low_energy_days = sorted(
            day for day, vals in dow_energy.items()
            if statistics.mean(vals) < threshold
        )

    if dow_mood:
        report.low_mood_days = sorted(
            day for day, vals in dow_mood.items()
            if statistics.mean(vals) < 1.5   # consistently "low"
        )

    if dow_sleep:
        report.poor_sleep_days = sorted(
            day for day, vals in dow_sleep.items()
            if statistics.mean(vals) < 5.5
        )

    # ── Correlations ──────────────────────────────────────────
    # Align sleep + energy on same dates
    date_sleep  = dict(sleep_series)
    date_energy = dict(energy_series)
    date_mood   = {d: float(v) for d, v in mood_series}
    date_stress = dict(stress_series)

    shared_se = [(date_sleep[d], date_energy[d])
                 for d in date_sleep if d in date_energy]
    if len(shared_se) >= 3:
        xs, ys = zip(*shared_se)
        report.sleep_energy_corr = _pearson(list(xs), list(ys))

    shared_sm = [(date_sleep[d], date_mood[d])
                 for d in date_sleep if d in date_mood]
    if len(shared_sm) >= 3:
        xs, ys = zip(*shared_sm)
        report.sleep_mood_corr = _pearson(list(xs), list(ys))

    shared_ste = [(date_stress[d], date_energy[d])
                  for d in date_stress if d in date_energy]
    if len(shared_ste) >= 3:
        xs, ys = zip(*shared_ste)
        report.stress_energy_corr = _pearson(list(xs), list(ys))

    # ── Streaks (from most recent backwards) ──────────────────
    for entry in logs:   # newest-first
        if _to_float(entry.get("energy")) is not None:
            if _to_float(entry.get("energy")) <= 4:
                report.consecutive_low_energy += 1
            else:
                break
    for entry in logs:
        if entry.get("mood"):
            if entry["mood"].lower() == "low":
                report.consecutive_low_mood += 1
            else:
                break
    for entry in logs:
        if _to_float(entry.get("sleep_hours")) is not None:
            if _to_float(entry.get("sleep_hours")) <= 5.0:
                report.consecutive_poor_sleep += 1
            else:
                break

    # ── Best / worst day ──────────────────────────────────────
    def _day_score(entry: dict) -> float:
        e = _to_float(entry.get("energy")) or 5.0
        m = float(_mood_to_int(entry.get("mood", "")) or 2)
        s = min(_to_float(entry.get("sleep_hours")) or 6.0, 9.0)
        return e * 0.4 + (m / 3.0 * 10) * 0.35 + (s / 9.0 * 10) * 0.25

    scored = [(e.get("date", ""), _day_score(e)) for e in chron]
    if scored:
        report.best_day  = max(scored, key=lambda x: x[1])[0]
        report.worst_day = min(scored, key=lambda x: x[1])[0]

    # ── Recovery signal ───────────────────────────────────────
    if len(chron) >= 4:
        recent_avg = statistics.mean(_day_score(e) for e in chron[-2:])
        prior_avg  = statistics.mean(_day_score(e) for e in chron[-4:-2])
        report.recovering = recent_avg > prior_avg + 0.5

    # ── Critical alerts ───────────────────────────────────────
    if report.consecutive_low_mood >= 4:
        report.critical_alerts.append(
            f"⚠️  {report.consecutive_low_mood} consecutive days of low mood — possible burnout/depression signal"
        )
    if report.consecutive_low_energy >= 4:
        report.critical_alerts.append(
            f"⚠️  {report.consecutive_low_energy} consecutive days of low energy — chronic fatigue pattern"
        )
    if report.consecutive_poor_sleep >= 4:
        report.critical_alerts.append(
            f"⚠️  {report.consecutive_poor_sleep} consecutive nights of poor sleep — sleep debt accumulating"
        )
    if report.energy_trend == "declining" and report.mood_trend == "declining":
        report.critical_alerts.append(
            "⚠️  Both energy AND mood are declining — compounding burnout risk"
        )
    if (report.avg_sleep_hours is not None and report.avg_sleep_hours < 5.0):
        report.critical_alerts.append(
            f"⚠️  Average sleep this week: {report.avg_sleep_hours}h — well below 7h minimum"
        )

    return report


# ──────────────────────────────────────────────
# PROMPT BLOCK FORMATTER
# ──────────────────────────────────────────────

def format_trend_block(report: TrendReport) -> str:
    """
    Format a TrendReport into a structured text block for AI injection.
    Returns empty string if no data.
    """
    if report.days_logged == 0:
        return ""

    lines = [
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"  📊  7-DAY TREND ANALYSIS  ({report.days_logged} days logged)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    # ── Critical alerts first ──────────────────────────────────
    if report.critical_alerts:
        lines.append("  🔴 TREND ALERTS:")
        for alert in report.critical_alerts:
            lines.append(f"     {alert}")

    # ── Averages ───────────────────────────────────────────────
    avg_parts = []
    if report.avg_energy      is not None: avg_parts.append(f"energy={report.avg_energy}/10")
    if report.avg_sleep_hours is not None: avg_parts.append(f"sleep={report.avg_sleep_hours}h/night")
    if report.avg_mood_score  is not None:
        mood_label = {1.0: "mostly low", 2.0: "mostly neutral", 3.0: "mostly good"}.get(
            round(report.avg_mood_score), f"{report.avg_mood_score:.1f}/3"
        )
        avg_parts.append(f"mood={mood_label}")
    if avg_parts:
        lines.append("  Weekly averages:  " + "  |  ".join(avg_parts))

    # ── Trend directions ───────────────────────────────────────
    _ICONS = {"improving": "📈", "declining": "📉", "stable": "➡️"}
    trend_parts = []
    if report.energy_trend != "stable" or report.mood_trend != "stable" or report.sleep_trend != "stable":
        trend_parts.append(f"energy {_ICONS[report.energy_trend]} {report.energy_trend}")
        trend_parts.append(f"mood {_ICONS[report.mood_trend]} {report.mood_trend}")
        trend_parts.append(f"sleep {_ICONS[report.sleep_trend]} {report.sleep_trend}")
        lines.append("  Trends:  " + "  |  ".join(trend_parts))

    # ── Streaks ────────────────────────────────────────────────
    if report.consecutive_low_energy >= 2:
        lines.append(f"  🔁 Low energy streak: {report.consecutive_low_energy} days in a row")
    if report.consecutive_low_mood >= 2:
        lines.append(f"  🔁 Low mood streak: {report.consecutive_low_mood} days in a row")
    if report.consecutive_poor_sleep >= 2:
        lines.append(f"  🔁 Poor sleep streak: {report.consecutive_poor_sleep} nights in a row")

    if report.recovering:
        lines.append("  ✅ Recovery signal: last 2 days better than previous 2")

    # ── Day-of-week patterns ───────────────────────────────────
    if report.low_energy_days:
        lines.append(f"  📅 Consistently low energy: {', '.join(report.low_energy_days)}")
    if report.low_mood_days:
        lines.append(f"  📅 Consistently low mood: {', '.join(report.low_mood_days)}")
    if report.poor_sleep_days:
        lines.append(f"  📅 Consistently poor sleep: {', '.join(report.poor_sleep_days)}")

    # ── Correlations ──────────────────────────────────────────
    if report.sleep_energy_corr is not None and abs(report.sleep_energy_corr) >= 0.4:
        direction = "more sleep → higher energy" if report.sleep_energy_corr > 0 else "sleep not driving energy (other factor)"
        lines.append(f"  🔗 Sleep↔Energy correlation: {report.sleep_energy_corr:+.2f}  ({direction})")

    if report.sleep_mood_corr is not None and abs(report.sleep_mood_corr) >= 0.4:
        direction = "more sleep → better mood" if report.sleep_mood_corr > 0 else "sleep not the main mood driver"
        lines.append(f"  🔗 Sleep↔Mood correlation: {report.sleep_mood_corr:+.2f}  ({direction})")

    if report.stress_energy_corr is not None and abs(report.stress_energy_corr) >= 0.4:
        direction = "higher stress → lower energy" if report.stress_energy_corr < 0 else "stress pattern unusual"
        lines.append(f"  🔗 Stress↔Energy correlation: {report.stress_energy_corr:+.2f}  ({direction})")

    # ── Best / worst day ──────────────────────────────────────
    if report.best_day and report.worst_day and report.best_day != report.worst_day:
        dow_best  = _dow(report.best_day)  or report.best_day
        dow_worst = _dow(report.worst_day) or report.worst_day
        lines.append(f"  🏆 Best day this week: {dow_best} ({report.best_day})")
        lines.append(f"  💀 Worst day this week: {dow_worst} ({report.worst_day})")

    lines += [
        "  ─────────────────────────────────────",
        "  AI INSTRUCTION: reference specific trends above when relevant.",
        "  e.g. 'Your data shows energy declines on Mondays — here is why...'",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    return "\n".join(lines)
