"""Nutrition log — save meals, summarise for Claude."""

from ..memory import store


def log_meal(description: str, calories: int | None = None):
    store.save_meal(description, calories)


def get_summary(days: int = 7) -> str | None:
    meals = store.get_meals(days=days)
    if not meals:
        return None
    lines = [f"Meal log (last {days} days):"]
    total_cal = 0
    for m in meals:
        ts = m["timestamp"][:16].replace("T", " ")
        cal_str = f" ({m['calories']} kcal)" if m["calories"] else ""
        lines.append(f"  [{ts}] {m['description']}{cal_str}")
        if m["calories"]:
            total_cal += m["calories"]
    if total_cal:
        lines.append(f"Total logged calories: {total_cal} kcal")
    return "\n".join(lines)


def detect_meal_log(intent: str) -> str | None:
    """
    If intent sounds like logging a meal, save it and return confirmation.
    Returns None if it's just a nutrition query (not a log command).
    """
    lower = intent.lower()
    log_triggers = ["i ate", "i had", "i just ate", "just had", "ate a", "had a", "log meal"]
    if any(t in lower for t in log_triggers):
        log_meal(intent)
        return f"Logged: {intent}"
    return None
