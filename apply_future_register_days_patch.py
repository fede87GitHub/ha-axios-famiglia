from __future__ import annotations

import argparse
import json
import py_compile
import shutil
import sys
from pathlib import Path

FILES = {
    "const": Path("custom_components/axios_famiglia/const.py"),
    "api": Path("custom_components/axios_famiglia/api.py"),
    "coordinator": Path("custom_components/axios_famiglia/coordinator.py"),
    "config_flow": Path("custom_components/axios_famiglia/config_flow.py"),
    "en": Path("custom_components/axios_famiglia/translations/en.json"),
    "it": Path("custom_components/axios_famiglia/translations/it.json"),
}


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def insert_after(text: str, anchor: str, addition: str, label: str) -> str:
    return replace_once(text, anchor, anchor + addition, label)


def patch_const(text: str) -> str:
    text = insert_after(
        text,
        'CONF_REGISTER_DAYS = "register_days"  # giorni di registro da considerare\n',
        'CONF_FUTURE_DAYS = "future_days"  # giorni futuri di registro da considerare\n',
        "const CONF_FUTURE_DAYS",
    )
    text = insert_after(
        text,
        'DEFAULT_REGISTER_DAYS = 14\n',
        'DEFAULT_FUTURE_DAYS = 7\n',
        "const DEFAULT_FUTURE_DAYS",
    )
    text = insert_after(
        text,
        'MIN_REGISTER_DAYS, MAX_REGISTER_DAYS = 1, 90\n',
        'MIN_FUTURE_DAYS, MAX_FUTURE_DAYS = 0, 30\n',
        "const future limits",
    )
    return text


def patch_coordinator(text: str) -> str:
    text = insert_after(
        text,
        '    CONF_CUSTOMER_ID,\n',
        '    CONF_FUTURE_DAYS,\n',
        "coordinator import CONF_FUTURE_DAYS",
    )
    text = insert_after(
        text,
        '    DEFAULT_COMMUNICATIONS_LIMIT,\n',
        '    DEFAULT_FUTURE_DAYS,\n',
        "coordinator import DEFAULT_FUTURE_DAYS",
    )
    text = insert_after(
        text,
        '        self.register_days = int(options.get(CONF_REGISTER_DAYS, DEFAULT_REGISTER_DAYS))\n',
        '        self.future_days = int(options.get(CONF_FUTURE_DAYS, DEFAULT_FUTURE_DAYS))\n',
        "coordinator self.future_days",
    )
    text = insert_after(
        text,
        '            register_days=self.register_days,\n',
        '            future_days=self.future_days,\n',
        "coordinator client future_days",
    )
    text = insert_after(
        text,
        '            "register_days": self.register_days,\n',
        '            "future_days": self.future_days,\n',
        "coordinator window future_days",
    )
    return text


def patch_config_flow(text: str) -> str:
    text = insert_after(
        text,
        '    CONF_CUSTOMER_ID,\n',
        '    CONF_FUTURE_DAYS,\n',
        "config_flow import CONF_FUTURE_DAYS",
    )
    text = insert_after(
        text,
        '    DEFAULT_COMMUNICATIONS_LIMIT,\n',
        '    DEFAULT_FUTURE_DAYS,\n',
        "config_flow import DEFAULT_FUTURE_DAYS",
    )
    text = insert_after(
        text,
        '    MAX_COMMUNICATIONS_LIMIT,\n',
        '    MAX_FUTURE_DAYS,\n',
        "config_flow import MAX_FUTURE_DAYS",
    )
    text = insert_after(
        text,
        '    MIN_COMMUNICATIONS_LIMIT,\n',
        '    MIN_FUTURE_DAYS,\n',
        "config_flow import MIN_FUTURE_DAYS",
    )

    anchor = '''            vol.Required(
                CONF_REGISTER_DAYS,
                default=options.get(CONF_REGISTER_DAYS, DEFAULT_REGISTER_DAYS),
            ): _number(MIN_REGISTER_DAYS, MAX_REGISTER_DAYS),
'''
    addition = '''            vol.Required(
                CONF_FUTURE_DAYS,
                default=options.get(CONF_FUTURE_DAYS, DEFAULT_FUTURE_DAYS),
            ): _number(MIN_FUTURE_DAYS, MAX_FUTURE_DAYS),
'''
    text = insert_after(text, anchor, addition, "config_flow future option")
    return text


def patch_api(text: str) -> str:
    text = replace_once(
        text,
        '        register_days: int = DEFAULT_REGISTER_DAYS,\n        communications_limit: int = DEFAULT_COMMUNICATIONS_LIMIT,\n',
        '        register_days: int = DEFAULT_REGISTER_DAYS,\n        future_days: int = 7,\n        communications_limit: int = DEFAULT_COMMUNICATIONS_LIMIT,\n',
        "api constructor future_days",
    )
    text = insert_after(
        text,
        '        self._register_days = register_days\n',
        '        self._future_days = future_days\n',
        "api self._future_days",
    )

    old_method = '''    async def _read_previous_weeks(self) -> tuple[list[dict[str, Any]], bool]:
        """Rows of the previous weeks that fall in the reading window.

        Returns (rows, complete). A week that cannot be read never breaks the update:
        its last known rows are used if there are any, otherwise it is skipped.
        """
        today = _today()
        this_monday = today - timedelta(days=today.weekday())
        mondays = past_week_mondays(today, self._register_days)
'''
    new_method = '''    async def _read_extra_weeks(self) -> tuple[list[dict[str, Any]], bool]:
        """Rows outside the current week that fall in the past/future windows.

        Returns (rows, complete). A week that cannot be read never breaks the update:
        its last known rows are used if there are any, otherwise it is skipped.
        Past weeks older than the immediately previous one are cached for six hours;
        the previous and future weeks are refreshed at every coordinator update.
        """
        today = _today()
        this_monday = today - timedelta(days=today.weekday())
        mondays = extra_week_mondays(today, self._register_days, self._future_days)
'''
    text = replace_once(text, old_method, new_method, "api read extra weeks")

    text = replace_once(
        text,
        '        older_rows, complete = await self._read_previous_weeks()\n        rows = merge_register_rows(current_rows, older_rows)\n',
        '        extra_rows, complete = await self._read_extra_weeks()\n        rows = merge_register_rows(current_rows, extra_rows)\n',
        "api async_get_data extra rows",
    )
    text = replace_once(
        text,
        '            "register": build_register(rows, self._register_days, partial=not complete),\n',
        '            "register": build_register(\n                rows, self._register_days, self._future_days, partial=not complete\n            ),\n',
        "api build_register call",
    )

    past_fn = '''def past_week_mondays(today: date, limit_days: int) -> list[date]:
    """Mondays (oldest first) of the weeks BEFORE the current one that overlap
    the last `limit_days` days. The current week is read by the main call."""
    if limit_days <= 0:
        return []
    this_monday = today - timedelta(days=today.weekday())
    first = today - timedelta(days=limit_days)
    monday = first - timedelta(days=first.weekday())
    mondays: list[date] = []
    while monday < this_monday:
        mondays.append(monday)
        monday += timedelta(days=7)
    return mondays
'''
    future_fns = past_fn + '''\n\ndef future_week_mondays(today: date, future_days: int) -> list[date]:
    """Mondays of future weeks overlapping the next `future_days` days.

    The current week is deliberately excluded because FAMILY_REGISTRO_CLASSE already
    returns it. For example, on Friday with future_days=7, the next Monday is included.
    """
    if future_days <= 0:
        return []
    this_monday = today - timedelta(days=today.weekday())
    last_day = today + timedelta(days=future_days)
    monday = this_monday + timedelta(days=7)
    mondays: list[date] = []
    while monday <= last_day:
        mondays.append(monday)
        monday += timedelta(days=7)
    return mondays


def extra_week_mondays(today: date, past_days: int, future_days: int) -> list[date]:
    """All non-current weeks required by the configured past/future windows."""
    return past_week_mondays(today, past_days) + future_week_mondays(today, future_days)
'''
    text = replace_once(text, past_fn, future_fns, "api future week functions")

    old_limit = '''def _limit_recent_days(days: list[dict[str, Any]], limit_days: int) -> list[dict[str, Any]]:
    """Keep only the register rows of the last `limit_days` days (newest first).

    If a date cannot be parsed, fall back to the first `limit_days` rows.
    """
    if limit_days <= 0 or not days:
        return days
    parsed = [(_parse_date(day["date"]), day) for day in days]
    if all(day_date is not None for day_date, _ in parsed):
        cutoff = _today() - timedelta(days=limit_days)
        recent = [(d, row) for d, row in parsed if d >= cutoff]
        recent.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in recent]
'''
    new_limit = '''def _limit_register_days(
    days: list[dict[str, Any]], past_days: int, future_days: int
) -> list[dict[str, Any]]:
    """Keep rows inside the rolling past/future window (newest first).

    If a date cannot be parsed, fall back to the first `past_days + future_days` rows.
    """
    if not days:
        return days
    parsed = [(_parse_date(day["date"]), day) for day in days]
    if all(day_date is not None for day_date, _ in parsed):
        today = _today()
        first_day = today - timedelta(days=max(0, past_days))
        last_day = today + timedelta(days=max(0, future_days))
        selected = [(d, row) for d, row in parsed if first_day <= d <= last_day]
        selected.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in selected]
'''
    text = replace_once(text, old_limit, new_limit, "api rolling window")
    text = replace_once(
        text,
        '        "falling back to the first %d rows",\n        days[0]["date"], limit_days,\n    )\n    return days[:limit_days]\n',
        '        "falling back to the first %d rows",\n        days[0]["date"], past_days + future_days,\n    )\n    return days[: past_days + future_days]\n',
        "api rolling fallback",
    )

    text = replace_once(
        text,
        '''def build_register(
    rows: list[dict[str, Any]], limit_days: int = DEFAULT_REGISTER_DAYS, partial: bool = False
) -> dict[str, Any]:
    total_rows = len(rows)
    days = _limit_recent_days(rows, limit_days)
    _LOGGER.debug(
        "Axios register: kept %d of %d rows (last %d days)",
        len(days), total_rows, limit_days,
    )
''',
        '''def build_register(
    rows: list[dict[str, Any]],
    limit_days: int = DEFAULT_REGISTER_DAYS,
    future_days: int = 0,
    partial: bool = False,
) -> dict[str, Any]:
    total_rows = len(rows)
    days = _limit_register_days(rows, limit_days, future_days)
    _LOGGER.debug(
        "Axios register: kept %d of %d rows (past %d days, future %d days)",
        len(days), total_rows, limit_days, future_days,
    )
''',
        "api build_register signature",
    )
    text = insert_after(
        text,
        '        "window_days": limit_days,\n',
        '        "future_days": future_days,\n',
        "api register future_days attribute",
    )
    text = replace_once(
        text,
        '''def parse_register(raw_html: str, limit_days: int = DEFAULT_REGISTER_DAYS) -> dict[str, Any]:
    """Single page (the current week): kept for compatibility."""
    return build_register(parse_register_rows(raw_html), limit_days)
''',
        '''def parse_register(
    raw_html: str,
    limit_days: int = DEFAULT_REGISTER_DAYS,
    future_days: int = 0,
) -> dict[str, Any]:
    """Single page (the current week): kept for compatibility."""
    return build_register(parse_register_rows(raw_html), limit_days, future_days)
''',
        "api parse_register compatibility",
    )
    return text


def patch_translation(path: Path, lang: str) -> None:
    obj = json.loads(path.read_text(encoding="utf-8"))
    data = obj["options"]["step"]["init"]["data"]
    desc = obj["options"]["step"]["init"].setdefault("data_description", {})
    new_data = {}
    for key, value in data.items():
        new_data[key] = value
        if key == "register_days":
            new_data["future_days"] = (
                "Future register days to read" if lang == "en" else "Giorni futuri di registro da leggere"
            )
    if "future_days" not in new_data:
        raise RuntimeError(f"{path}: register_days not found")
    obj["options"]["step"]["init"]["data"] = new_data
    desc["future_days"] = (
        "How many future register days are read for homework, tests, annotations, notes and lesson topics (0 to 30). "
        "Seven days include the following school week when needed."
        if lang == "en"
        else "Quanti giorni futuri del registro vengono letti per compiti, verifiche, annotazioni, note e argomenti (da 0 a 30). "
        "Sette giorni includono la settimana scolastica successiva quando necessario."
    )
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply future-register-days support to Axios Famiglia")
    parser.add_argument("repo", nargs="?", default=".", help="Repository root")
    parser.add_argument("--check", action="store_true", help="Validate only; do not write")
    args = parser.parse_args()
    root = Path(args.repo).resolve()

    missing = [str(path) for path in FILES.values() if not (root / path).is_file()]
    if missing:
        raise SystemExit("Missing files:\n- " + "\n- ".join(missing))

    original = {name: (root / path).read_text(encoding="utf-8") for name, path in FILES.items()}
    patched = {
        "const": patch_const(original["const"]),
        "api": patch_api(original["api"]),
        "coordinator": patch_coordinator(original["coordinator"]),
        "config_flow": patch_config_flow(original["config_flow"]),
    }

    if args.check:
        print("All Python anchors matched. No files written.")
        return 0

    backup_root = root / ".future_days_backup"
    if backup_root.exists():
        shutil.rmtree(backup_root)
    for name, rel in FILES.items():
        dst = backup_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dst)

    for name, text in patched.items():
        (root / FILES[name]).write_text(text, encoding="utf-8")
    patch_translation(root / FILES["en"], "en")
    patch_translation(root / FILES["it"], "it")

    for key in ("api", "const", "coordinator", "config_flow"):
        py_compile.compile(str(root / FILES[key]), doraise=True)
    for key in ("en", "it"):
        json.loads((root / FILES[key]).read_text(encoding="utf-8"))

    print("Patched and validated:")
    for rel in FILES.values():
        print(f"- {rel}")
    print(f"Backup: {backup_root}")
    print("Suggested manifest version for this bug fix: 1.5.1")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
