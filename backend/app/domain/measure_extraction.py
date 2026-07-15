import json
import re
import sqlite3
from pathlib import Path
from statistics import median

import pdfplumber


LEFT_X0 = 100.0
RIGHT_X1 = 540.0
BOTTOM_LIMIT = 730.0
TOP_PADDING = 4.0
BOTTOM_PADDING = 4.0
LINE_TOP_TOLERANCE = 3.0
POSITION_CLUSTER_TOLERANCE = 1.5
THIN_RECT_MAX_THICKNESS = 1.0
HORIZONTAL_RULE_MIN_WIDTH = 40.0
VERTICAL_RULE_MAX_WIDTH = 1.0
HEADER_CUTOFF = 120.0
FOOTER_CUTOFF = 730.0
LEFT_MARGIN_CUTOFF = 140.0
PORTFOLIO_MIN_SIZE = 11.5
MEASURE_MIN_SIZE = 9.0
MEASURE_MAX_SIZE = 11.5
MODERN_SECTION_HEADERS = {"Receipts ($m)", "Payments ($m)", "Related payments ($m)", "Related receipts ($m)"}
LEGACY_SECTION_HEADERS = {"Revenue ($m)", "Expense ($m)", "Capital ($m)", "Related revenue ($m)", "Related expense ($m)", "Related capital ($m)"}
SECTION_HEADERS = MODERN_SECTION_HEADERS | LEGACY_SECTION_HEADERS
MODERN_SECTION_TITLE_TO_MODE = {
    "Receipt Measures": "receipt",
    "Payment Measures": "payment",
    "Part 1: Receipt Measures": "receipt",
    "Part 2: Payment Measures": "payment",
}
LEGACY_SECTION_TITLE_TO_MODE = {
    "Revenue Measures": "receipt",
    "Expense Measures": "payment",
    "Capital Measures": "payment",
    "Part 1: Revenue Measures": "receipt",
    "Part 2: Expense Measures": "payment",
    "Part 3: Capital Measures": "payment",
}
SECTION_TITLE_TO_MODE = MODERN_SECTION_TITLE_TO_MODE | LEGACY_SECTION_TITLE_TO_MODE
YEAR_LABELS = ["2023-24", "2024-25", "2025-26", "2026-27", "2027-28"]
YEAR_RE = re.compile(r"^\d{4}-\d{2}$")
VALUE_RE = re.compile(r"^(?:-?(?:\d+(?:\.\d+)?)|nfp|\.{2}|\*|-)$")
AMOUNT_RE = re.compile(r"\$(?P<amount>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>million|billion)", re.IGNORECASE)
DURATION_FROM_RE = re.compile(r"over\s+(?P<duration>\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen)\s+years?\s+from\s+(?P<start_year>\d{4}-\d{2})", re.IGNORECASE)
SINGLE_YEAR_RE = re.compile(r"in\s+(?P<start_year>\d{4}-\d{2})", re.IGNORECASE)
COMPONENT_GROUP_INTRO_RE = re.compile(
    r"\b(?:include|includes|including|provide|provides|providing|comprise|comprises|comprising|consist of|consists of|consisting of|support|supports|supporting|conditional|conditions)\b",
    re.IGNORECASE,
)
TAIL_NARRATIVE_RE = re.compile(
    r"^(?:The Government|This measure|Partial savings|The Treasury|This Measure|These measures)",
    re.IGNORECASE,
)
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
}
TOTAL_LABELS = {
    "Total – Receipts",
    "Total - Receipts",
    "Total – Payments",
    "Total - Payments",
    "Total – Revenue",
    "Total - Revenue",
    "Total – Expense",
    "Total - Expense",
    "Total – Capital",
    "Total - Capital",
}
SKIP_PREFIXES = (
    "Receipts",
    "Payments",
    "Revenue",
    "Expense",
    "Capital",
    "Related payments",
    "Related receipts",
    "Related expense",
    "Related revenue",
    "Related capital",
    "Total ",
    "Table ",
    "Appendix",
    "Page ",
)
SKIP_EXACT_TITLES = {"Receipt Measures", "Payment Measures", "Revenue Measures", "Expense Measures", "Capital Measures"}


def normalize_text(text: str) -> str:
    text = " ".join(text.split())
    text = re.sub(r"\s*([’'])\s*", r"\1", text)
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = text.replace("‑", "-")
    text = text.replace("−", "-")
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    return text


def normalize_portfolio_heading(text: str) -> str:
    normalized = normalize_text(text)

    while True:
        collapsed = re.sub(r"\b([A-Z])\s+([A-Z][A-Z’']*)\b", r"\1\2", normalized)
        if collapsed == normalized:
            break
        normalized = collapsed

    normalized = re.sub(r"\s*-\s*", "-", normalized)
    return normalized


def normalize_related_measure_text(text: str) -> str:
    normalized = normalize_text(text).strip(" \t\n\r.,;:()[]{}\"'-")
    return normalized


def detect_document_vocabulary(pdf: pdfplumber.pdf.PDF) -> str:
    max_pages = min(len(pdf.pages), 40)
    for page_number in range(max_pages):
        for line in extract_styled_lines(pdf.pages[page_number]):
            text = line["text"]
            if text in LEGACY_SECTION_HEADERS or text in LEGACY_SECTION_TITLE_TO_MODE:
                return "legacy"
            if text in MODERN_SECTION_HEADERS or text in MODERN_SECTION_TITLE_TO_MODE:
                return "modern"
    return "modern"


def section_title_map_for_vocabulary(vocabulary: str) -> dict[str, str]:
    return LEGACY_SECTION_TITLE_TO_MODE if vocabulary == "legacy" else MODERN_SECTION_TITLE_TO_MODE


def is_financial_header_text(text: str) -> bool:
    return text in SECTION_HEADERS


def financial_header_to_impact_type(text: str) -> str | None:
    if text in {"Receipts ($m)", "Revenue ($m)", "Related receipts ($m)", "Related revenue ($m)"}:
        return "Receipt"
    if text in {"Payments ($m)", "Expense ($m)", "Capital ($m)", "Related payments ($m)", "Related expense ($m)", "Related capital ($m)"}:
        return "Payment"
    return None


def is_related_financial_header_text(text: str) -> bool:
    return text in {"Related receipts ($m)", "Related revenue ($m)", "Related payments ($m)", "Related expense ($m)", "Related capital ($m)"}


def _is_component_start(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("•") or stripped.startswith("-")


def _component_marker(line: str) -> str | None:
    stripped = line.lstrip()
    if stripped.startswith("•"):
        return "•"
    if stripped.startswith("-"):
        return "-"
    return None


def _component_level(marker: str | None) -> int:
    if marker == "•":
        return 1
    if marker == "-":
        return 2
    return 0


def _clean_component_line(line: str) -> str:
    stripped = line.lstrip()
    if stripped.startswith("•"):
        stripped = stripped[1:]
    elif stripped.startswith("-"):
        stripped = stripped[1:]
    return normalize_text(stripped)


def _is_component_group_intro(line: str) -> bool:
    normalized = normalize_text(line)
    if not normalized or _is_component_start(normalized):
        return False
    if not normalized.endswith(":"):
        return False

    intro_text = normalized[:-1].strip()
    if not intro_text:
        return False

    if COMPONENT_GROUP_INTRO_RE.search(intro_text):
        return True

    if intro_text.startswith("$"):
        return True

    words = intro_text.split()
    return bool(words) and len(words) <= 6 and intro_text[0].isupper()


def _is_group_intro_candidate_start(line: str) -> bool:
    normalized = normalize_text(line)
    if not normalized or _is_component_start(normalized):
        return False
    return normalized.startswith("$") or normalized[0].isupper()


def _consume_component_group_intro(lines: list[str], start_index: int) -> tuple[str, int] | None:
    if start_index >= len(lines) or not _is_group_intro_candidate_start(lines[start_index]):
        return None

    collected: list[str] = []
    index = start_index
    while index < len(lines) and not _is_component_start(lines[index]):
        collected.append(lines[index])
        combined = normalize_text(" ".join(collected))
        if _is_component_group_intro(combined):
            return combined, index + 1
        index += 1

    return None


def _is_tail_narrative_start(line: str) -> bool:
    normalized = normalize_text(line)
    if not normalized or _is_component_start(normalized):
        return False
    return bool(TAIL_NARRATIVE_RE.match(normalized))


def _parse_component_amount(component_text: str) -> tuple[float | None, str | None]:
    match = AMOUNT_RE.search(component_text)
    if match is None:
        return None, None
    amount = float(match.group("amount").replace(",", ""))
    unit = match.group("unit").lower()
    amount_in_millions = amount * 1000 if unit == "billion" else amount
    return amount_in_millions, normalize_text(match.group(0))


def _parse_component_schedule(component_text: str) -> tuple[str | None, int | None]:
    duration_match = DURATION_FROM_RE.search(component_text)
    if duration_match is not None:
        duration_text = duration_match.group("duration").lower()
        duration_years = int(duration_text) if duration_text.isdigit() else NUMBER_WORDS.get(duration_text)
        return duration_match.group("start_year"), duration_years

    single_year_match = SINGLE_YEAR_RE.search(component_text)
    if single_year_match is not None:
        return single_year_match.group("start_year"), 1

    return None, None


def _allocate_component_impacts(amount_in_millions: float | None, start_year: str | None, duration_years: int | None) -> list[float | int]:
    allocated = [0.0] * len(YEAR_LABELS)
    if amount_in_millions is None or start_year is None or not duration_years:
        return allocated
    if start_year not in YEAR_LABELS:
        return allocated

    annual_amount = amount_in_millions / duration_years
    start_index = YEAR_LABELS.index(start_year)
    end_index = min(start_index + duration_years, len(YEAR_LABELS))

    for index in range(start_index, end_index):
        allocated[index] = annual_amount

    return [int(value) if float(value).is_integer() else round(value, 1) for value in allocated]


def _impact_value_kind(value: int | float | str) -> str:
    if isinstance(value, (int, float)):
        return "numeric"
    if value == "nfp":
        return "nfp"
    if value in {"", None}:
        return "blank"
    return "other"


def _component_marker_name(marker: str) -> str:
    return "dot" if marker == "•" else "dash"


def extract_measure_components(measure_text: str, document_section: str) -> list[dict]:
    lines = [line.strip() for line in measure_text.splitlines() if line.strip()]
    components: list[dict] = []
    current_lines: list[str] = []
    current_marker: str | None = None

    def flush_component():
        nonlocal current_lines, current_marker
        if not current_lines:
            return

        component_text = normalize_text(" ".join(current_lines))
        if current_marker is not None:
            components.append({"text": component_text, "marker": current_marker})

        current_lines = []
        current_marker = None

    index = 0
    while index < len(lines):
        line = lines[index]
        if _is_component_start(line):
            flush_component()
            current_lines = [_clean_component_line(line)]
            current_marker = _component_marker(line)
            index += 1
            continue

        intro = _consume_component_group_intro(lines, index)
        if intro is not None:
            _, next_index = intro
            flush_component()
            index = next_index
            continue

        if current_lines and _is_tail_narrative_start(line):
            flush_component()
            index += 1
            continue

        if current_lines:
            current_lines.append(normalize_text(line))
        index += 1

    flush_component()

    impact_type = "Payment" if document_section == "payment" else "Receipt"
    parsed_components: list[dict] = []
    top_level_ordinal = 0
    child_ordinals: dict[int, int] = {}
    current_parent_ordinal: int | None = None

    for component in components:
        component_text = component["text"]
        marker = component["marker"]
        level = _component_level(marker)
        if level == 1:
            top_level_ordinal += 1
            ordinal = top_level_ordinal
            parent_ordinal = None
            current_parent_ordinal = ordinal
        elif current_parent_ordinal is not None:
            parent_ordinal = current_parent_ordinal
            child_ordinals[parent_ordinal] = child_ordinals.get(parent_ordinal, 0) + 1
            ordinal = child_ordinals[parent_ordinal]
        else:
            continue

        amount_value, amount_text = _parse_component_amount(component_text)
        start_year, duration_years = _parse_component_schedule(component_text)
        allocation_status = "allocated" if amount_value is not None and start_year and duration_years else "unallocated"
        parsed_components.append(
            {
                "parent_ordinal": parent_ordinal,
                "level": level,
                "marker": _component_marker_name(marker),
                "ordinal": ordinal,
                "component_text": component_text,
                "amount_raw": amount_text,
                "amount_million": amount_value,
                "start_fiscal_year": start_year,
                "duration_years": duration_years,
                "impact_type": impact_type,
                "allocation_status": allocation_status,
                "impact_values": _allocate_component_impacts(amount_value, start_year, duration_years) if amount_value is not None else [],
            }
        )

    return parsed_components


def is_bold(fontname: str) -> bool:
    return "bold" in fontname.lower()


def is_italic(fontname: str) -> bool:
    lowered = fontname.lower()
    return "italic" in lowered or "oblique" in lowered


def extract_related_measure_titles_from_words(words: list[dict]) -> list[str]:
    grouped_lines: list[dict] = []
    for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
        text = normalize_text(word["text"])
        if not text:
            continue
        if not grouped_lines or abs(word["top"] - grouped_lines[-1]["top"]) > LINE_TOP_TOLERANCE:
            grouped_lines.append({"top": float(word["top"]), "words": [word]})
        else:
            grouped_lines[-1]["words"].append(word)

    extracted_titles: list[str] = []
    current_parts: list[str] = []

    def flush_current_title() -> None:
        nonlocal current_parts
        if not current_parts:
            return
        title = normalize_related_measure_text(" ".join(current_parts))
        if title:
            extracted_titles.append(title)
        current_parts = []

    for line in grouped_lines:
        line_words = sorted(line["words"], key=lambda item: item["x0"])
        line_index = 0

        if current_parts:
            if line_index >= len(line_words) or not is_italic(line_words[line_index].get("fontname", "")):
                flush_current_title()

        while line_index < len(line_words):
            word = line_words[line_index]
            text = normalize_text(word["text"])
            is_word_italic = is_italic(word.get("fontname", ""))

            if not is_word_italic:
                flush_current_title()
                line_index += 1
                continue

            current_parts.append(text)
            line_index += 1

            if "." in text:
                flush_current_title()
                continue

            while line_index < len(line_words):
                next_word = line_words[line_index]
                next_text = normalize_text(next_word["text"])
                next_is_italic = is_italic(next_word.get("fontname", ""))
                if not next_is_italic:
                    flush_current_title()
                    break

                current_parts.append(next_text)
                line_index += 1
                if "." in next_text:
                    flush_current_title()
                    break

        # If the line ends while still inside an italic title, keep the run open so
        # a wrapped title on the next line is joined with a plain space.

    flush_current_title()
    return extracted_titles


def starts_with_upper_alpha(text: str) -> bool:
    for char in text:
        if char.isalpha():
            return char.isupper()
    return False


def is_year_header(row: list[str]) -> bool:
    return bool(row) and row[0] == "" and len(row) == 6 and all(YEAR_RE.match(value) for value in row[1:])


def is_empty_value_row(row: list[str]) -> bool:
    return len(row) == 6 and not any(row[1:])


def merge_department_name(base: str, continuation: str) -> str:
    return normalize_text(f"{base} {continuation}")


def parse_impact_value(value: str) -> int | float | str:
    normalized = normalize_text(value)
    if normalized in {"", "-"}:
        return 0
    if normalized in {"..", "nfp", "*"}:
        return normalized
    normalized = normalized.replace(",", "")
    try:
        numeric = float(normalized)
    except ValueError:
        return normalized
    if numeric.is_integer():
        return int(numeric)
    return numeric


def cluster_positions(values: list[float], tolerance: float = POSITION_CLUSTER_TOLERANCE) -> list[float]:
    if not values:
        return []

    clusters: list[list[float]] = [[values[0]]]
    for value in values[1:]:
        if abs(value - clusters[-1][-1]) <= tolerance:
            clusters[-1].append(value)
        else:
            clusters.append([value])

    return [round(median(cluster), 2) for cluster in clusters]


def should_skip_line(text: str) -> bool:
    if text in SKIP_EXACT_TITLES:
        return True
    if any(text.startswith(prefix) for prefix in SKIP_PREFIXES):
        return True
    if text.startswith("|"):
        return True
    return False


def extract_styled_lines(page: pdfplumber.page.Page) -> list[dict]:
    words = page.extract_words(extra_attrs=["fontname", "size"])
    groups: list[dict] = []

    for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
        if word["top"] < HEADER_CUTOFF or word["top"] > FOOTER_CUTOFF:
            continue
        text = normalize_text(word["text"])
        if not text:
            continue
        if not groups or abs(word["top"] - groups[-1]["words"][0]["top"]) > LINE_TOP_TOLERANCE:
            groups.append({"words": [word]})
        else:
            groups[-1]["words"].append(word)

    styled_lines = []
    for group in groups:
        words_in_line = sorted(group["words"], key=lambda item: item["x0"])
        fontnames = [word["fontname"] for word in words_in_line]
        sizes = [float(word["size"]) for word in words_in_line]
        styled_lines.append(
            {
                "text": normalize_text(" ".join(word["text"] for word in words_in_line)),
                "x0": min(word["x0"] for word in words_in_line),
                "x1": max(word["x1"] for word in words_in_line),
                "top": min(word["top"] for word in words_in_line),
                "bottom": max(word["bottom"] for word in words_in_line),
                "max_size": max(sizes),
                "bold_ratio": sum(1 for fontname in fontnames if is_bold(fontname)) / len(fontnames),
            }
        )

    return styled_lines


def is_portfolio_line(line: dict) -> bool:
    return (
        line["x0"] <= LEFT_MARGIN_CUTOFF
        and line["bold_ratio"] >= 0.8
        and line["max_size"] >= PORTFOLIO_MIN_SIZE
        and starts_with_upper_alpha(line["text"])
        and not should_skip_line(line["text"])
    )


def is_measure_line(line: dict) -> bool:
    return (
        line["x0"] <= LEFT_MARGIN_CUTOFF
        and line["bold_ratio"] >= 0.8
        and MEASURE_MIN_SIZE <= line["max_size"] < MEASURE_MAX_SIZE
        and not should_skip_line(line["text"])
    )


def is_section_heading(line: dict) -> bool:
    return line["text"] in SECTION_TITLE_TO_MODE


def has_financial_table_header(lines: list[dict], start_index: int) -> bool:
    end_index = min(len(lines), start_index + 6)
    for index in range(start_index, end_index):
        candidate = lines[index]
        if is_financial_header_text(candidate["text"]):
            return True
        if index > start_index and (is_portfolio_line(candidate) or is_measure_line(candidate) or is_section_heading(candidate)):
            break
    return False


def consume_block(lines: list[dict], start_index: int, predicate) -> tuple[str, dict, int]:
    block_lines = [lines[start_index]]
    next_index = start_index + 1

    while next_index < len(lines):
        candidate = lines[next_index]
        previous = block_lines[-1]
        if not predicate(candidate):
            break
        if candidate["top"] - previous["bottom"] > 14.0:
            break
        block_lines.append(candidate)
        next_index += 1

    text = normalize_text(" ".join(line["text"] for line in block_lines))
    location = {
        "page": None,
        "x0": round(min(line["x0"] for line in block_lines), 2),
        "top": round(min(line["top"] for line in block_lines), 2),
        "x1": round(max(line["x1"] for line in block_lines), 2),
        "bottom": round(max(line["bottom"] for line in block_lines), 2),
    }
    return text, location, next_index


def detect_section_boundaries(pdf: pdfplumber.pdf.PDF) -> list[dict]:
    boundaries: list[dict] = []
    vocabulary = detect_document_vocabulary(pdf)
    section_title_map = section_title_map_for_vocabulary(vocabulary)
    current_mode = "receipt"

    for page_number, page in enumerate(pdf.pages, start=1):
        for line in extract_styled_lines(page):
            mode = section_title_map.get(line["text"])
            if mode and mode != current_mode:
                boundaries.append({"page": page_number, "mode": mode})
                current_mode = mode
                break

    return boundaries


def mode_for_page(page_number: int, boundaries: list[dict]) -> str:
    mode = "receipt"
    for boundary in boundaries:
        if page_number >= boundary["page"]:
            mode = boundary["mode"]
        else:
            break
    return mode


def build_measure_locations(pdf: pdfplumber.pdf.PDF) -> list[dict]:
    measures: list[dict] = []
    current_portfolio: str | None = None
    boundaries = detect_section_boundaries(pdf)

    for page_number, page in enumerate(pdf.pages, start=1):
        lines = extract_styled_lines(page)
        line_index = 0

        while line_index < len(lines):
            line = lines[line_index]

            if is_portfolio_line(line):
                portfolio_text, _, next_index = consume_block(lines, line_index, is_portfolio_line)
                current_portfolio = normalize_portfolio_heading(portfolio_text)
                line_index = next_index
                continue

            if current_portfolio and is_measure_line(line):
                measure_text, location, next_index = consume_block(lines, line_index, is_measure_line)
                if not has_financial_table_header(lines, next_index):
                    line_index = next_index
                    continue
                location["page"] = page_number
                measures.append(
                    {
                        "portfolio": current_portfolio,
                        "measure_title": measure_text,
                        "location": location,
                        "document_section": mode_for_page(page_number, boundaries),
                    }
                )
                line_index = next_index
                continue

            line_index += 1

    measures.sort(key=lambda item: (item["location"]["page"], item["location"]["top"], item["measure_title"]))
    return measures


def next_heading_top(measures: list[dict], current_index: int) -> float:
    current = measures[current_index]["location"]
    for later in measures[current_index + 1 :]:
        candidate = later["location"]
        if candidate["page"] == current["page"] and candidate["top"] > current["top"]:
            return float(candidate["top"])
    return BOTTOM_LIMIT


def find_stop_heading_top(page: pdfplumber.page.Page, start_top: float) -> float | None:
    for line in extract_styled_lines(page):
        if line["top"] <= start_top:
            continue
        if is_portfolio_line(line) or is_measure_line(line) or is_section_heading(line):
            return float(line["top"])
    return None


def find_table_rules(page: pdfplumber.page.Page, start_top: float, end_top: float) -> dict:
    relevant_rects = [
        rect
        for rect in page.rects
        if start_top <= rect["top"] <= end_top and LEFT_X0 - 5 <= rect["x0"] <= RIGHT_X1 + 5
    ]

    horizontal_segments = [
        rect
        for rect in relevant_rects
        if rect["height"] <= THIN_RECT_MAX_THICKNESS and rect["width"] >= HORIZONTAL_RULE_MIN_WIDTH
    ]
    vertical_segments = [
        rect
        for rect in relevant_rects
        if rect["width"] <= VERTICAL_RULE_MAX_WIDTH and rect["height"] <= THIN_RECT_MAX_THICKNESS
    ]

    horizontal_positions = cluster_positions(sorted(rect["top"] for rect in horizontal_segments))
    vertical_positions = cluster_positions(sorted(rect["x0"] for rect in vertical_segments))

    if horizontal_segments:
        left_bound = round(min(rect["x0"] for rect in horizontal_segments), 2)
        right_bound = round(max(rect["x1"] for rect in horizontal_segments), 2)
    else:
        left_bound = LEFT_X0
        right_bound = RIGHT_X1

    explicit_vertical_lines = [left_bound, *vertical_positions, right_bound]
    return {
        "horizontal": horizontal_positions,
        "vertical": explicit_vertical_lines,
        "left_bound": left_bound,
        "right_bound": right_bound,
    }


def extract_lines(page: pdfplumber.page.Page) -> list[str]:
    words = page.extract_words(x_tolerance=2, y_tolerance=2, keep_blank_chars=False)
    grouped: list[dict] = []
    for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
        text = normalize_text(word["text"])
        if not text:
            continue
        if not grouped or abs(word["top"] - grouped[-1]["top"]) > LINE_TOP_TOLERANCE:
            grouped.append({"top": word["top"], "words": [word]})
        else:
            grouped[-1]["words"].append(word)
    return [
        normalize_text(" ".join(word["text"] for word in sorted(line["words"], key=lambda item: item["x0"])))
        for line in grouped
    ]


def clamp_crop_bbox(
    page: pdfplumber.page.Page,
    x0: float,
    top: float,
    x1: float,
    bottom: float,
) -> tuple[float, float, float, float] | None:
    page_x0, page_top, page_x1, page_bottom = page.bbox
    clamped_x0 = max(page_x0, x0)
    clamped_top = max(page_top, top)
    clamped_x1 = min(page_x1, x1)
    clamped_bottom = min(page_bottom, bottom)
    if clamped_x0 >= clamped_x1 or clamped_top >= clamped_bottom:
        return None
    return (clamped_x0, clamped_top, clamped_x1, clamped_bottom)


def extract_table_using_rules(page: pdfplumber.page.Page, rules: dict) -> list[list[str]]:
    if len(rules["horizontal"]) < 2 or len(rules["vertical"]) < 2:
        return []
    settings = {
        "vertical_strategy": "explicit",
        "horizontal_strategy": "explicit",
        "explicit_horizontal_lines": rules["horizontal"],
        "explicit_vertical_lines": rules["vertical"],
        "snap_tolerance": 6,
        "join_tolerance": 6,
        "intersection_tolerance": 6,
        "text_x_tolerance": 3,
        "text_y_tolerance": 3,
    }
    return page.extract_table(settings) or []


def split_multiline_row(label: str, values: list[str]) -> list[list[str]]:
    label_lines = [normalize_text(part) for part in label.split("\n") if normalize_text(part)]
    if not label_lines:
        return [["", *values]]

    rows: list[list[str]] = []
    if label_lines[0] in SECTION_HEADERS and len(label_lines) > 1:
        rows.append([label_lines[0], "", "", "", "", ""])
        rows.append([label_lines[1], *values])
        for continuation in label_lines[2:]:
            rows.append([continuation, "", "", "", "", ""])
        return rows

    rows.append([label_lines[0], *values])
    for continuation in label_lines[1:]:
        rows.append([continuation, "", "", "", "", ""])
    return rows


def normalize_table_from_grid(table: list[list[str]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table:
        if not row:
            continue
        padded = list(row[:6]) + [""] * max(0, 6 - len(row))
        cleaned = [(cell or "").strip() for cell in padded[:6]]
        if not any(cleaned):
            continue
        label = cleaned[0]
        values = [normalize_text(cell) for cell in cleaned[1:]]
        if label:
            rows.extend(split_multiline_row(label, values))
        else:
            rows.append(["", *values])
    return rows


def tokenise_row(text: str) -> tuple[str, list[str]]:
    tokens = text.split()
    trailing_values: list[str] = []
    split_index = len(tokens)

    for index in range(len(tokens) - 1, -1, -1):
        token = tokens[index]
        if VALUE_RE.match(token) and len(trailing_values) < 5:
            trailing_values.insert(0, token)
            split_index = index
            continue
        break

    label = normalize_text(" ".join(tokens[:split_index]))
    return label, trailing_values


def looks_like_continuation(text: str) -> bool:
    tokens = text.split()
    if not tokens:
        return False
    if text.startswith("and "):
        return True
    return len(tokens) <= 4 and text[0].isupper()


def extract_table_rows_from_lines(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    started = False
    for line in lines:
        if not line:
            continue
        tokens = line.split()
        if len(tokens) == 5 and all(YEAR_RE.match(token) for token in tokens):
            rows.append(["", *tokens])
            started = True
            continue
        if line in SECTION_HEADERS:
            continue
        if is_related_financial_header_text(line):
            if started:
                rows.append([line, "", "", "", "", ""])
            continue

        label, trailing_values = tokenise_row(line)
        if trailing_values:
            started = True
            rows.append([label, *([""] * (5 - len(trailing_values))), *trailing_values][-6:])
            continue
        if started and looks_like_continuation(line):
            rows.append([line, "", "", "", "", ""])
            continue
        if started:
            break

    return rows


def extract_measure_table(pdf: pdfplumber.pdf.PDF, measures: list[dict], measure_index: int) -> dict:
    measure = measures[measure_index]
    location = measure["location"]
    page = pdf.pages[location["page"] - 1]
    start_top = float(location["bottom"]) + TOP_PADDING
    next_title_top = next_heading_top(measures, measure_index) - BOTTOM_PADDING
    rules = find_table_rules(page, start_top, next_title_top)
    end_top = next_title_top
    if rules["horizontal"]:
        end_top = min(next_title_top, max(rules["horizontal"]) + BOTTOM_PADDING)
    if end_top <= start_top:
        end_top = BOTTOM_LIMIT

    crop_bbox = clamp_crop_bbox(page, rules["left_bound"], start_top, rules["right_bound"], end_top)
    if crop_bbox is None:
        return {
            "portfolio": measure["portfolio"],
            "measure_title": measure["measure_title"],
            "document_section": measure["document_section"],
            "page": location["page"],
            "title_location": location,
            "table_bbox": {
                "x0": round(rules["left_bound"], 2),
                "top": round(start_top, 2),
                "x1": round(rules["right_bound"], 2),
                "bottom": round(end_top, 2),
            },
            "table_rows": [],
        }

    crop = page.crop(crop_bbox)
    lines = extract_lines(crop)
    grid_rows = extract_table_using_rules(crop, rules)
    rows = normalize_table_from_grid(grid_rows)
    if not rows:
        rows = extract_table_rows_from_lines(lines)

    return {
        "portfolio": measure["portfolio"],
        "measure_title": measure["measure_title"],
        "document_section": measure["document_section"],
        "page": location["page"],
        "title_location": location,
        "table_bbox": {
            "x0": round(rules["left_bound"], 2),
            "top": round(start_top, 2),
            "x1": round(rules["right_bound"], 2),
            "bottom": round(end_top, 2),
        },
        "table_rows": rows,
    }


def iter_measure_text_crops(
    pdf: pdfplumber.pdf.PDF,
    measures: list[dict],
    measure_index: int,
    table_bottom: float,
):
    measure = measures[measure_index]
    current_location = measure["location"]
    next_measure = measures[measure_index + 1] if measure_index + 1 < len(measures) else None

    for page_number in range(current_location["page"], len(pdf.pages) + 1):
        page = pdf.pages[page_number - 1]
        start_top = table_bottom + TOP_PADDING if page_number == current_location["page"] else HEADER_CUTOFF
        stop_top = find_stop_heading_top(page, start_top)
        if next_measure and page_number == next_measure["location"]["page"]:
            candidate_stop = float(next_measure["location"]["top"])
            stop_top = min(stop_top, candidate_stop) if stop_top is not None else candidate_stop
        if stop_top is None:
            stop_top = FOOTER_CUTOFF
        if stop_top <= start_top:
            break

        crop_bbox = clamp_crop_bbox(page, LEFT_X0, start_top, RIGHT_X1, stop_top - BOTTOM_PADDING)
        if crop_bbox is None:
            break

        crop = page.crop(crop_bbox)
        yield crop

        if find_stop_heading_top(page, start_top) is not None or (
            next_measure and page_number >= next_measure["location"]["page"]
        ):
            break


def extract_measure_text(pdf: pdfplumber.pdf.PDF, measures: list[dict], measure_index: int, table_bottom: float) -> str:
    text_lines: list[str] = []

    for crop in iter_measure_text_crops(pdf, measures, measure_index, table_bottom):
        page_lines = [line for line in extract_lines(crop) if line and line not in SECTION_HEADERS]
        text_lines.extend(page_lines)

    return "\n".join(text_lines).strip()


def extract_related_measures(
    pdf: pdfplumber.pdf.PDF,
    measures: list[dict],
    measure_index: int,
    table_bottom: float,
) -> list[str]:
    related_measures: list[str] = []
    seen: set[str] = set()

    for crop in iter_measure_text_crops(pdf, measures, measure_index, table_bottom):
        words = crop.extract_words(
            x_tolerance=2,
            y_tolerance=2,
            keep_blank_chars=False,
            extra_attrs=["fontname"],
        )
        for related_measure in extract_related_measure_titles_from_words(words):
            if related_measure not in seen:
                seen.add(related_measure)
                related_measures.append(related_measure)

    return related_measures


def parse_headline_financials_from_rows(rows: list[list[str]], document_section: str) -> list[dict]:
    headline_financials: list[dict] = []
    primary_header = "Payments ($m)" if document_section == "payment" else "Receipts ($m)"
    primary_impact_type = financial_header_to_impact_type(primary_header) or ("Payment" if document_section == "payment" else "Receipt")
    current_impact_type = primary_impact_type
    current_is_related = 0
    current_year_labels = YEAR_LABELS.copy()
    pending_department: str | None = None
    current_entry: dict | None = None

    def merge_value_cells(existing_values: list[dict], incoming_values: list[dict]) -> None:
        for existing_value, incoming_value in zip(existing_values, incoming_values, strict=False):
            existing_kind = existing_value["value_kind"]
            incoming_kind = incoming_value["value_kind"]

            existing_numeric = existing_value["value_numeric_million"]
            incoming_numeric = incoming_value["value_numeric_million"]

            should_replace = False
            if existing_kind == "blank" and incoming_kind != "blank":
                should_replace = True
            elif existing_kind == "numeric" and existing_numeric == 0 and incoming_kind != "numeric":
                should_replace = True
            elif existing_kind == "numeric" and existing_numeric == 0 and incoming_kind == "numeric" and incoming_numeric not in (None, 0):
                should_replace = True
            elif existing_kind in {"nfp", "other"} and incoming_kind == "numeric" and incoming_numeric not in (None, 0):
                should_replace = True

            if should_replace:
                existing_value.update(incoming_value)

    for row in rows:
        if not row or len(row) != 6:
            continue

        label = normalize_text(row[0])
        values = [parse_impact_value(value) for value in row[1:]]

        if is_year_header(row):
            current_impact_type = primary_impact_type
            current_is_related = 0
            current_year_labels = [normalize_text(value) for value in row[1:]]
            pending_department = None
            current_entry = None
            continue

        header_impact_type = financial_header_to_impact_type(label)
        if header_impact_type is not None:
            current_impact_type = header_impact_type
            current_is_related = 1 if is_related_financial_header_text(label) else 0
            pending_department = None
            current_entry = None
            continue

        if not label or label in TOTAL_LABELS:
            pending_department = None if label in TOTAL_LABELS else pending_department
            current_entry = None if label in TOTAL_LABELS else current_entry
            continue

        if is_empty_value_row(row):
            if pending_department and current_entry is not None:
                merged_department = merge_department_name(pending_department, label)
                current_entry["department_name"] = merged_department
                pending_department = merged_department

                duplicate_entry = next(
                    (
                        entry
                        for entry in headline_financials
                        if entry is not current_entry
                        and entry["impact_type"] == current_entry["impact_type"]
                        and entry["is_related"] == current_entry["is_related"]
                        and entry["department_name"] == current_entry["department_name"]
                    ),
                    None,
                )
                if duplicate_entry is not None:
                    merge_value_cells(duplicate_entry["values"], current_entry["values"])
                    headline_financials.remove(current_entry)
                    current_entry = duplicate_entry
            continue

        current_entry = {
            "impact_type": current_impact_type,
            "is_related": current_is_related,
            "department_name": label,
            "ordinal": len(headline_financials) + 1,
            "values": [
                {
                    "fiscal_year": fiscal_year,
                    "value_kind": _impact_value_kind(value),
                    "value_numeric_million": value if isinstance(value, (int, float)) else None,
                    "value_raw": None if isinstance(value, (int, float)) else str(value),
                }
                for fiscal_year, value in zip(current_year_labels, values, strict=False)
            ],
        }

        existing_entry = next(
            (
                entry
                for entry in headline_financials
                if entry["impact_type"] == current_entry["impact_type"]
                and entry["is_related"] == current_entry["is_related"]
                and entry["department_name"] == current_entry["department_name"]
            ),
            None,
        )
        if existing_entry is not None:
            merge_value_cells(existing_entry["values"], current_entry["values"])
            current_entry = existing_entry
            pending_department = label
            continue

        headline_financials.append(current_entry)
        pending_department = label
    return headline_financials


def parse_impacts_from_rows(rows: list[list[str]], document_section: str) -> dict[str, dict[str, list[int | float | str]]]:
    impacts: dict[str, dict[str, list[int | float | str]]] = {}
    for headline_financial in parse_headline_financials_from_rows(rows, document_section):
        bucket = impacts.setdefault(headline_financial["impact_type"], {})
        bucket[headline_financial["department_name"]] = [
            value_cell["value_numeric_million"] if value_cell["value_kind"] == "numeric" else value_cell["value_raw"]
            for value_cell in headline_financial["values"]
        ]
    return impacts


def _schema_path() -> Path:
    return Path(__file__).resolve().parents[1] / "infrastructure" / "db" / "schema.sql"


def _ensure_database_schema(connection: sqlite3.Connection) -> None:
    schema_path = _schema_path()
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.executescript(schema_path.read_text(encoding="utf-8"))


def _replace_source_document(
    connection: sqlite3.Connection,
    pdf_path: str,
    budget_year: str,
    paper_code: str | None = None,
    title: str | None = None,
) -> int:
    connection.execute("DELETE FROM source_document WHERE file_path = ?", (pdf_path,))
    cursor = connection.execute(
        """
        INSERT INTO source_document (budget_year, paper_code, title, file_path)
        VALUES (?, ?, ?, ?)
        """,
        (budget_year, paper_code, title, pdf_path),
    )
    return int(cursor.lastrowid)


def _insert_measure(connection: sqlite3.Connection, source_document_id: int, record: dict) -> int:
    cursor = connection.execute(
        """
        INSERT INTO measure (
            source_document_id,
            portfolio_name,
            measure_title,
            document_section,
            source_page,
            full_measure_text
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            source_document_id,
            record["portfolio_name"],
            record["measure_title"],
            record["document_section"],
            record["source_page"],
            record["full_measure_text"],
        ),
    )
    return int(cursor.lastrowid)


def _insert_headline_financials(connection: sqlite3.Connection, measure_id: int, headline_financials: list[dict]) -> None:
    for headline_financial in headline_financials:
        cursor = connection.execute(
            """
            INSERT INTO measure_headline_financial (
                measure_id,
                impact_type,
                department_name,
                is_related,
                ordinal
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                measure_id,
                headline_financial["impact_type"],
                headline_financial["department_name"],
                headline_financial["is_related"],
                headline_financial["ordinal"],
            ),
        )
        headline_financial_id = int(cursor.lastrowid)
        for value_cell in headline_financial["values"]:
            connection.execute(
                """
                INSERT INTO measure_headline_financial_value (
                    headline_financial_id,
                    fiscal_year,
                    value_kind,
                    value_numeric_million,
                    value_raw
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    headline_financial_id,
                    value_cell["fiscal_year"],
                    value_cell["value_kind"],
                    value_cell["value_numeric_million"],
                    value_cell["value_raw"],
                ),
            )


def _insert_components(connection: sqlite3.Connection, measure_id: int, components: list[dict]) -> None:
    inserted_top_level_ids: dict[int, int] = {}
    for component in components:
        parent_component_id = None
        parent_ordinal = component.get("parent_ordinal")
        if parent_ordinal is not None:
            parent_component_id = inserted_top_level_ids.get(parent_ordinal)
            if parent_component_id is None:
                continue

        cursor = connection.execute(
            """
            INSERT INTO measure_component (
                measure_id,
                parent_component_id,
                level,
                marker,
                ordinal,
                component_text,
                amount_raw,
                amount_million,
                start_fiscal_year,
                duration_years,
                allocation_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                measure_id,
                parent_component_id,
                component["level"],
                component["marker"],
                component["ordinal"],
                component["component_text"],
                component["amount_raw"],
                component["amount_million"],
                component["start_fiscal_year"],
                component["duration_years"],
                component["allocation_status"],
            ),
        )
        component_id = int(cursor.lastrowid)
        if component["level"] == 1:
            inserted_top_level_ids[component["ordinal"]] = component_id

        for fiscal_year, impact_value in zip(YEAR_LABELS, component["impact_values"], strict=False):
            value_kind = _impact_value_kind(impact_value)
            connection.execute(
                """
                INSERT INTO measure_component_impact (
                    component_id,
                    impact_type,
                    fiscal_year,
                    value_kind,
                    value_numeric_million,
                    value_raw
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    component_id,
                    component["impact_type"],
                    fiscal_year,
                    value_kind,
                    impact_value if isinstance(impact_value, (int, float)) else None,
                    None if isinstance(impact_value, (int, float)) else str(impact_value),
                ),
            )


def _insert_related_measures(connection: sqlite3.Connection, measure_id: int, related_measures: list[str]) -> None:
    for ordinal, related_measure_title in enumerate(related_measures, start=1):
        connection.execute(
            """
            INSERT OR IGNORE INTO measure_related_measure (
                measure_id,
                ordinal,
                related_measure_title
            )
            VALUES (?, ?, ?)
            """,
            (measure_id, ordinal, related_measure_title),
        )


def write_measure_records_sqlite(
    pdf_path: str,
    db_path: str,
    budget_year: str,
    paper_code: str | None = None,
    title: str | None = None,
) -> int:
    records = extract_measure_records(pdf_path)
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_file) as connection:
        _ensure_database_schema(connection)
        source_document_id = _replace_source_document(
            connection,
            pdf_path=pdf_path,
            budget_year=budget_year,
            paper_code=paper_code,
            title=title,
        )
        for record in records:
            measure_id = _insert_measure(connection, source_document_id, record)
            _insert_headline_financials(connection, measure_id, record["headline_financials"])
            _insert_components(connection, measure_id, record["components"])
            _insert_related_measures(connection, measure_id, record["related_measures"])
        connection.commit()

    return len(records)


def extract_measure_records(pdf_path: str) -> list[dict]:
    with pdfplumber.open(pdf_path) as pdf:
        measures = build_measure_locations(pdf)
        records = []
        for measure_index in range(len(measures)):
            extracted = extract_measure_table(pdf, measures, measure_index)
            measure_text = extract_measure_text(pdf, measures, measure_index, extracted["table_bbox"]["bottom"])
            records.append(
                {
                    "portfolio_name": extracted["portfolio"],
                    "measure_title": extracted["measure_title"],
                    "document_section": extracted["document_section"],
                    "source_page": extracted["page"],
                    "full_measure_text": measure_text,
                    "related_measures": extract_related_measures(pdf, measures, measure_index, extracted["table_bbox"]["bottom"]),
                    "components": extract_measure_components(measure_text, extracted["document_section"]),
                    "headline_financials": parse_headline_financials_from_rows(extracted["table_rows"], extracted["document_section"]),
                }
            )
    return records


def write_measure_records_json(pdf_path: str, output_path: str) -> None:
    records = extract_measure_records(pdf_path)
    nested: dict[str, dict[str, dict]] = {}
    for record in records:
        portfolio_bucket = nested.setdefault(record["portfolio_name"], {})
        measure_bucket = portfolio_bucket.setdefault(
            record["measure_title"],
            {
                "document_section": record["document_section"],
                "page": record["source_page"],
                "measure_text": record["full_measure_text"],
            },
        )
        for headline_financial in record["headline_financials"]:
            impact_bucket = measure_bucket.setdefault(headline_financial["impact_type"], {})
            impact_bucket[headline_financial["department_name"]] = [
                value_cell["value_numeric_million"] if value_cell["value_kind"] == "numeric" else value_cell["value_raw"]
                for value_cell in headline_financial["values"]
            ]
    Path(output_path).write_text(json.dumps(nested, indent=2, ensure_ascii=True) + "\n")