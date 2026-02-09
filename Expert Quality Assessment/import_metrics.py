"""Импорт/трансформация метрик качества из markdown-таблицы в CSV."""

import csv
from pathlib import Path


# Базовые пути к входному файлу и результатам конвертации.
BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "Таблица экспертной оценки качества ответов.md"
METRICS_PATH = BASE_DIR / "metrics.csv"
TRANSFORMED_PATH = BASE_DIR / "metrics_transformed.csv"


# Соответствие заголовков таблицы: исходные -> внутренние ключи.
HEADER_MAPPING = {
    "№": "Num",
    "Категория": "Topic",
    "LCS": "LCS",
    "SGS (кач.)": "SGS",
    "NVS": "NVS",
    "LCV (оценка)": "LCV",
    "LCV": "LCV_Value",
    "SCS (баллы 1-6)": "SCS",
    "CRS (оценка)": "CRS",
    "HRS (галл.)": "HRS",
    "HRS (описание)": "HRS_Desc",
}

# Маппинг текстовых оценок в числовую шкалу.
TEXT_SCORE = {
    "высокая": 2,
    "средняя": 1,
    "низкая": 0,
}

# Веса метрик для итогового качества (Q).
WEIGHTS = {
    "LCS": 0.25,
    "SGS": 0.15,
    "NVS": 0.10,
    "LCV": 0.15,
    "SCS": 0.10,
    "CRS": 0.10,
    "HRS": 0.10,
}


def parse_markdown_table(lines):
    """Парсит markdown-таблицу и возвращает заголовок и строки данных."""
    header = None
    data_rows = []

    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line.startswith("|"):
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if header is None:
            if "Категория" in cells:
                header = cells
            continue

        # Skip the separator row immediately after header
        if all(cell and set(cell) <= {"-"} for cell in cells):
            continue

        if header and len(cells) >= len(header):
            data_rows.append(dict(zip(header, cells)))

    return header, data_rows


def extract_metrics(rows):
    """Преобразует строки таблицы в унифицированные ключи метрик."""
    extracted = []
    for row in rows:
        item = {}
        for source_key, target_key in HEADER_MAPPING.items():
            item[target_key] = row.get(source_key, "").strip()
        extracted.append(item)
    return extracted


def normalize_text(value):
    """Нормализует текстовое значение для сопоставления."""
    return value.strip().lower()


def map_text_score(value):
    """Переводит текстовые оценки/цифры в числовую шкалу."""
    normalized = normalize_text(value)
    if normalized in TEXT_SCORE:
        return TEXT_SCORE[normalized]
    if normalized.isdigit():
        return int(normalized)
    return ""


def map_direct_score(value):
    """Извлекает целочисленную оценку, если значение числовое."""
    normalized = normalize_text(value)
    if normalized.isdigit():
        return int(normalized)
    return ""


def map_scs_score(value):
    """Конвертирует SCS (1-6) в шкалу 0-2."""
    normalized = normalize_text(value)
    if not normalized.isdigit():
        return ""
    score = int(normalized)
    if score >= 5:
        return 2
    if score >= 3:
        return 1
    return 0


def map_hrs_score(value, description):
    """Определяет HRS с учетом текста и описания галлюцинаций."""
    normalized = normalize_text(value)
    has_description = bool(description.strip())
    if not normalized and not has_description:
        return ""
    if normalized == "нет" and not has_description:
        return 1
    return 0


def is_numeric(value):
    """Проверяет, что значение является числом."""
    return isinstance(value, (int, float))


def normalize_score(metric, score, max_score=2):
    """Нормализует оценку в диапазон 0..1 (HRS оставляет как есть)."""
    if not is_numeric(score):
        return ""
    if metric == "HRS":
        return score
    return score / max_score


def calculate_quality(normalized_metrics):
    """Считает итоговую метрику качества с учетом весов."""
    weighted_sum = 0.0
    has_values = False
    for metric, score in normalized_metrics.items():
        normalized_score = normalize_score(metric, score)
        if not is_numeric(normalized_score):
            continue
        weight = WEIGHTS.get(metric)
        if weight is None:
            continue
        weighted_sum += weight * normalized_score
        has_values = True
    if not has_values:
        return ""
    return round(weighted_sum, 4)


def transform_metrics(rows):
    """Трансформирует сырые значения метрик и рассчитывает Q."""
    transformed = []
    for row in rows:
        normalized = {
            "LCS": map_direct_score(row.get("LCS", "")),
            "SGS": map_text_score(row.get("SGS", "")),
            "NVS": map_direct_score(row.get("NVS", "")),
            "LCV": map_text_score(row.get("LCV", "")),
            "SCS": map_scs_score(row.get("SCS", "")),
            "CRS": map_text_score(row.get("CRS", "")),
            "HRS": map_hrs_score(
                row.get("HRS", ""),
                row.get("HRS_Desc", ""),
            ),
        }
        quality = calculate_quality(normalized)
        transformed.append(
            {
                "Num": row.get("Num", ""),
                "Topic": row.get("Topic", ""),
                **normalized,
                "Q": quality,
            }
        )
    return transformed


def calculate_average_quality(rows):
    """Считает среднее значение Q по итоговой таблице."""
    total = 0.0
    count = 0
    for row in rows:
        value = row.get("Q", "")
        if value is None:
            continue
        value = str(value).strip().replace(",", ".")
        if not value:
            continue
        try:
            total += float(value)
            count += 1
        except ValueError:
            continue
    if count == 0:
        return ""
    return round(total / count, 4)


def main():
    """Точка входа для запуска отдельных этапов обработки."""
    # Переключатели стадий: импорт markdown -> CSV -> трансформация -> среднее.
    RUN_IMPORT = False
    RUN_TRANSFORM = False
    RUN_AVERAGE = True

    extracted = []
    if RUN_IMPORT:
        lines = INPUT_PATH.read_text(encoding="utf-8").splitlines()
        _, rows = parse_markdown_table(lines)
        extracted = extract_metrics(rows)

        METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with METRICS_PATH.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=list(HEADER_MAPPING.values()),
            )
            writer.writeheader()
            writer.writerows(extracted)

        print(f"Wrote {len(extracted)} rows to {METRICS_PATH}")

    if RUN_TRANSFORM:
        if not METRICS_PATH.exists():
            raise FileNotFoundError(
                f"Missing source file for transform: {METRICS_PATH}"
            )

        with METRICS_PATH.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            transformed = transform_metrics(list(reader))

        with TRANSFORMED_PATH.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "Num",
                    "Topic",
                    "LCS",
                    "SGS",
                    "NVS",
                    "LCV",
                    "SCS",
                    "CRS",
                    "HRS",
                    "Q",
                ],
            )
            writer.writeheader()
            writer.writerows(transformed)

        print(f"Wrote {len(transformed)} rows to {TRANSFORMED_PATH}")

    if RUN_AVERAGE:
        if not TRANSFORMED_PATH.exists():
            raise FileNotFoundError(
                f"Missing transformed file for averaging: {TRANSFORMED_PATH}"
            )
        with TRANSFORMED_PATH.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            average_quality = calculate_average_quality(list(reader))
        if average_quality == "":
            print("Average Q: no valid values")
        else:
            print(f"Average Q: {average_quality}")


if __name__ == "__main__":
    main()
