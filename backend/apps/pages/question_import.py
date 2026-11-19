"""Bounded, read-only spreadsheet import. Workbook content is data, never instructions."""

import csv
import io
import math
import re
import unicodedata
import uuid
from datetime import date, datetime
from pathlib import Path
from zipfile import BadZipFile, ZipFile

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 20 * 1024 * 1024
MAX_SHEETS = 20
MAX_ROWS = 1000
MAX_COLUMNS = 40
MAX_CELLS = 20000
MAX_TEXT = 1_000_000
MAX_QUESTIONS = 60
OPTION_FIELDS = [f"option_{letter.lower()}" for letter in "ABCDEF"]
MAPPING_FIELDS = ["question", *OPTION_FIELDS, "answer", "subject", "explanation"]
FIELD_LABELS = {"question": "Question", "answer": "Correct answer", "subject": "Subject / section (optional)", "explanation": "Explanation (optional)", **{field: f"Option {letter}" for field, letter in zip(OPTION_FIELDS, "ABCDEF")}}
HEADER_ALIASES = {
    "question": ["question", "questiontext", "prompt", "stem", "q"],
    "answer": ["answer", "correctanswer", "correctoption", "answerkey", "key", "solution"],
    "subject": ["subject", "section", "category", "topic", "skill"],
    "explanation": ["explanation", "rationale", "reason", "answerexplanation"],
    **{field: [f"option{letter.lower()}", f"answer{letter.lower()}", f"choice{letter.lower()}", letter.lower(), f"option{index}", f"choice{index}"] for index, (field, letter) in enumerate(zip(OPTION_FIELDS, "ABCDEF"), 1)},
}


class ImportProblem(ValueError):
    pass


def normalise(value):
    return " ".join(unicodedata.normalize("NFKC", str(value)).casefold().split())


def cell_text(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ImportProblem("The workbook contains a non-finite number. Replace it with plain text or a valid number.")
        return str(int(value)) if value.is_integer() else str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value).strip()


def read_upload(upload):
    suffix = Path(upload.name).suffix.casefold()
    if suffix not in {".xlsx", ".xlsm", ".xls", ".csv"}:
        raise ImportProblem("Upload an .xlsx, .xlsm, .xls or UTF-8 .csv file.")
    if upload.size > MAX_FILE_BYTES:
        raise ImportProblem("The upload must be 2 MB or smaller.")
    content = upload.read(MAX_FILE_BYTES + 1)
    if not content or len(content) > MAX_FILE_BYTES:
        raise ImportProblem("The upload is empty or exceeds 2 MB.")
    try:
        if suffix == ".csv":
            sheets = _read_csv(content)
        elif suffix == ".xls":
            sheets = _read_xls(content)
        else:
            sheets = _read_xlsx(content)
        cells = sum(len(row) for sheet in sheets for row in sheet["rows"])
        characters = sum(len(value) for sheet in sheets for row in sheet["rows"] for value in row)
        if cells > MAX_CELLS or characters > MAX_TEXT:
            raise ImportProblem("The workbook is too large to import. Keep at most 20,000 cells and 1 million text characters.")
        if not any(any(value for value in row) for sheet in sheets for row in sheet["rows"]):
            raise ImportProblem("The workbook has no populated cells.")
        return sheets
    except ImportProblem:
        raise
    except Exception as exc:
        # Parser errors must not expose file content or internal paths.
        raise ImportProblem("This file could not be read. Use an unencrypted Excel workbook or UTF-8 CSV, or download our template.") from exc


def _read_csv(content):
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportProblem("Save the CSV using UTF-8 encoding and upload it again.") from exc
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = []
    for row in csv.reader(io.StringIO(text), dialect):
        if len(row) > MAX_COLUMNS or len(rows) >= MAX_ROWS:
            raise ImportProblem("Use at most 1,000 rows and 40 columns per sheet.")
        if any(len(value) > 5000 for value in row):
            raise ImportProblem("A cell exceeds 5,000 characters. Shorten it and upload again.")
        rows.append([value.strip() for value in row])
    return [{"name": "CSV", "rows": rows, "invalid_cells": []}]


def _read_xlsx(content):
    from openpyxl import load_workbook

    try:
        with ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            if len(entries) > 2000 or sum(entry.file_size for entry in entries) > MAX_UNCOMPRESSED_BYTES:
                raise ImportProblem("The workbook expands beyond the import limit. Remove unused sheets, formatting and embedded objects.")
            if any(entry.flag_bits & 1 for entry in entries):
                raise ImportProblem("Password-protected workbooks cannot be imported. Upload an unencrypted copy.")
    except BadZipFile as exc:
        raise ImportProblem("This is not a readable Excel workbook. Export it as .xlsx or CSV and try again.") from exc
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=False, keep_links=False)
    try:
        if len(workbook.worksheets) > MAX_SHEETS:
            raise ImportProblem("Use a workbook with at most 20 worksheets.")
        sheets = []
        cells_seen = 0
        text_seen = 0
        for worksheet in workbook.worksheets:
            rows, invalid = [], []
            # Ignore inflated formatting dimensions but bound actual iteration explicitly.
            worksheet.reset_dimensions()
            for row_index, cells in enumerate(worksheet.iter_rows(), 1):
                if row_index > MAX_ROWS or len(cells) > MAX_COLUMNS:
                    raise ImportProblem("Use at most 1,000 rows and 40 columns per sheet.")
                values = []
                for column, cell in enumerate(cells):
                    value = cell_text(cell.value)
                    if value and (row_index > MAX_ROWS or column >= MAX_COLUMNS):
                        raise ImportProblem("Use at most 1,000 rows and 40 columns per sheet.")
                    if len(value) > 5000:
                        raise ImportProblem("A cell exceeds 5,000 characters. Shorten it and upload again.")
                    if cell.data_type in {"f", "e"}:
                        invalid.append([row_index, column])
                    values.append(value)
                while values and not values[-1]:
                    values.pop()
                rows.append(values)
                cells_seen += len(values)
                text_seen += sum(len(value) for value in values)
                if cells_seen > MAX_CELLS or text_seen > MAX_TEXT:
                    raise ImportProblem("The workbook exceeds the import size limits. Upload only the sheets containing your questions.")
            while rows and not any(rows[-1]):
                rows.pop()
            sheets.append({"name": worksheet.title, "rows": rows, "invalid_cells": invalid})
        return sheets
    finally:
        workbook.close()


def _read_xls(content):
    import xlrd

    workbook = xlrd.open_workbook(file_contents=content, on_demand=True)
    try:
        if workbook.nsheets > MAX_SHEETS:
            raise ImportProblem("Use a workbook with at most 20 worksheets.")
        sheets = []
        cells_seen = 0
        for worksheet in workbook.sheets():
            if worksheet.nrows > MAX_ROWS or worksheet.ncols > MAX_COLUMNS:
                raise ImportProblem("Use at most 1,000 rows and 40 columns per sheet.")
            cells_seen += worksheet.nrows * worksheet.ncols
            if cells_seen > MAX_CELLS:
                raise ImportProblem("Keep the workbook within 20,000 cells.")
            rows, invalid = [], []
            for row_index in range(worksheet.nrows):
                values = []
                for column in range(worksheet.ncols):
                    cell = worksheet.cell(row_index, column)
                    if cell.ctype == xlrd.XL_CELL_ERROR:
                        invalid.append([row_index+1, column])
                    value = cell.value
                    if cell.ctype == xlrd.XL_CELL_BOOLEAN:
                        value = bool(value)
                    elif cell.ctype == xlrd.XL_CELL_DATE:
                        value = xlrd.xldate.xldate_as_datetime(value, workbook.datemode)
                    value = cell_text(value)
                    if len(value) > 5000:
                        raise ImportProblem("A cell exceeds 5,000 characters.")
                    values.append(value)
                rows.append(values)
            sheets.append({"name": worksheet.name, "rows": rows, "invalid_cells": invalid})
        return sheets
    finally:
        workbook.release_resources()


def default_mapping(sheet, header_row):
    headers = sheet["rows"][header_row-1] if len(sheet["rows"]) >= header_row else []
    normal_headers = [re.sub(r"[^a-z0-9]", "", normalise(value)) for value in headers]
    mapping = {"answer_format": "auto"}
    for field, aliases in HEADER_ALIASES.items():
        matches = [index for index, header in enumerate(normal_headers) if header in aliases]
        if len(matches) == 1:
            mapping[field] = str(matches[0])
    return mapping


def validate_questions(sheet, header_row, mapping):
    """All rows must validate; never silently drop invalid questions or change answer keys."""
    questions, errors, seen = [], [], set()
    invalid_cells = {tuple(cell) for cell in sheet["invalid_cells"]}
    for row_number, row in enumerate(sheet["rows"][header_row:], header_row+1):
        values = {field: row[int(mapping[field])] if mapping.get(field) not in (None, "") and int(mapping[field]) < len(row) else "" for field in MAPPING_FIELDS}
        if not any(values.values()):
            continue
        issues = []
        if any((row_number, int(mapping[field])) in invalid_cells for field in MAPPING_FIELDS if mapping.get(field) not in (None, "")):
            issues.append("Mapped cells contain a formula or Excel error. Replace them with plain values.")
        if not values["question"]:
            issues.append("Question is missing.")
        elif len(values["question"]) > 4000:
            issues.append("Question exceeds 4,000 characters.")
        labelled_options = [(letter, values[field]) for field, letter in zip(OPTION_FIELDS, "ABCDEF") if values[field]]
        if len(labelled_options) < 2:
            issues.append("Provide at least two answer options.")
        options = [value for _, value in labelled_options]
        if any(len(value) > 500 for value in options):
            issues.append("Each option must contain at most 500 characters.")
        if len({normalise(option) for option in options}) != len(options):
            issues.append("Answer options must be distinct.")
        if len(values["subject"]) > 80 or len(values["explanation"]) > 4000:
            issues.append("Subject must be at most 80 characters and explanation at most 4,000.")
        answer = resolve_answer(values["answer"], labelled_options, mapping.get("answer_format", "auto"))
        if answer is None:
            issues.append("Correct answer is missing, does not match an option, or is ambiguous. Check the answer format.")
        signature = (normalise(values["question"]), tuple(sorted(normalise(option) for option in options)))
        if signature in seen:
            issues.append("This question and its options duplicate an earlier row.")
        seen.add(signature)
        if issues:
            errors.append({"row": row_number, "messages": issues})
            continue
        questions.append({
            "section_type": "recruiter_custom", "difficulty": "custom", "seed": "",
            "payload": {"question_id": str(uuid.uuid4()), "section_type": "recruiter_custom",
                "prompt": {"instruction": "Choose one answer.", "question": values["question"], "explanation": values["explanation"]},
                "options": options, "metadata": {"subject": values["subject"] or "Custom questions", "source_row": row_number, "provenance": "recruiter_upload"}},
            "correct_answer": {"answer": answer},
        })
    if not questions and not errors:
        errors.append({"row": header_row, "messages": ["No question rows were found below this header. Select the correct sheet, header row and columns."]})
    if len(questions) + len(errors) > MAX_QUESTIONS:
        errors.append({"row": 0, "messages": [f"Use at most {MAX_QUESTIONS} questions per assessment. Split this sheet into smaller assessments."]})
    return questions, errors


def resolve_answer(raw, labelled_options, answer_format):
    if not raw:
        return None
    raw_normalised = normalise(raw)
    candidates = set()
    if answer_format in {"auto", "text"}:
        candidates.update(value for _, value in labelled_options if normalise(value) == raw_normalised)
    if answer_format in {"auto", "letter"}:
        letter = re.sub(r"^(?:option|choice)\s*", "", raw_normalised).strip(" .):(").upper()
        candidates.update(value for label, value in labelled_options if label == letter)
    if answer_format in {"auto", "number"} and raw_normalised in {"1", "2", "3", "4", "5", "6"}:
        letter = "ABCDEF"[int(raw_normalised)-1]
        candidates.update(value for label, value in labelled_options if label == letter)
    return next(iter(candidates)) if len(candidates) == 1 else None
