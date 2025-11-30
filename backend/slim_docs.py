import re
from pathlib import Path

IN_PATH = Path("nflreadpy_schema.md")
OUT_PATH = Path("nflreadpy_schema_columns_only.md")

text = IN_PATH.read_text(encoding="utf-8")

out_parts = [
    "# nflreadpy Column Reference (compressed)\n\n",
    "For each loader below, this lists **only** the column names returned in the DataFrame.\n",
    "Use this as a contract to avoid hallucinating non-existent columns.\n\n",
]

# Split by headings like "## load_pbp"
sections = re.split(r"(^## .+$)", text, flags=re.MULTILINE)

current_loader = None

for chunk in sections:
    if chunk.startswith("## "):
        # e.g., "## load_pbp"
        current_loader = chunk.strip().lstrip("#").strip()
        continue

    if not current_loader:
        continue

    # Find markdown table in this section
    # We'll grab the header row + data rows between the first two '---' lines and a blank line.
    lines = chunk.splitlines()
    table_lines = []
    in_table = False
    for line in lines:
        if "|" in line:
            in_table = True
            table_lines.append(line)
        elif in_table and line.strip() == "":
            break

    if not table_lines:
        continue

    # Parse header to find the column-name column index (Field/field)
    header = table_lines[0]
    header_cells = [c.strip() for c in header.strip().strip("|").split("|")]
    try:
        name_idx = header_cells.index("Field")
    except ValueError:
        try:
            name_idx = header_cells.index("field")
        except ValueError:
            continue  # no obvious name column

    # Collect column names from subsequent rows (skip header + separator)
    col_names = []
    for row in table_lines[2:]:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) <= name_idx:
            continue
        name = cells[name_idx]
        if name and name.lower() != "field":
            col_names.append(name)

    if col_names:
        loader_name = current_loader  # e.g. "load_pbp"
        out_parts.append(f"## {loader_name} columns\n\n")
        # Wrap long lines a bit for readability
        out_parts.append(", ".join(col_names) + "\n\n")

OUT_PATH.write_text("".join(out_parts), encoding="utf-8")
print(f"Wrote {OUT_PATH.resolve()}")
