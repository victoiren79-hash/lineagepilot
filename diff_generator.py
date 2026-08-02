"""
Generates a corrected version of a downstream SQL file after a column rename,
plus a unified diff showing before/after.

Run standalone to test:
    py -3.11 diff_generator.py
"""
import difflib
import re


def generate_fix(old_column: str, new_column: str, file_path: str, file_content: str, risk: str) -> dict:
    """
    Returns {"fixed_content": "...", "diff": "..."}

    LOW risk  -> alias the new name to the old one, so nothing else in the
                 file needs to change (minimal, safe edit).
    HIGH risk -> replace the column properly everywhere it's used (join
                 conditions, GROUP BY, etc.), since aliasing alone could
                 silently break the join/aggregation logic.
    """
    lines = file_content.splitlines(keepends=True)

    if risk == "LOW":
        # Replace a bare column reference with "new_col as old_col" so
        # downstream code referencing old_col by name keeps working.
        pattern = re.compile(rf"\b{re.escape(old_column)}\b")
        fixed_lines = []
        replaced_once = False
        for line in lines:
            if not replaced_once and pattern.search(line):
                line = pattern.sub(f"{new_column} as {old_column}", line, count=1)
                replaced_once = True
            fixed_lines.append(line)
        fixed_content = "".join(fixed_lines)
    else:
        # HIGH risk: replace every occurrence of the old column name with
        # the new one, since it's used structurally (join key / group by).
        pattern = re.compile(rf"\b{re.escape(old_column)}\b")
        fixed_content = pattern.sub(new_column, file_content)

    diff = "".join(difflib.unified_diff(
        file_content.splitlines(keepends=True),
        fixed_content.splitlines(keepends=True),
        fromfile=f"{file_path} (before)",
        tofile=f"{file_path} (after)",
    ))

    return {"fixed_content": fixed_content, "diff": diff}


if __name__ == "__main__":
    with open("models/stg_orders_v2.sql") as f:
        safe_content = f.read()
    result = generate_fix("user_id", "customer_id", "models/stg_orders_v2.sql", safe_content, "LOW")
    print("SAFE case diff:\n")
    print(result["diff"])

    with open("models/fct_revenue_v2.sql") as f:
        risky_content = f.read()
    result2 = generate_fix("user_id", "customer_id", "models/fct_revenue_v2.sql", risky_content, "HIGH")
    print("\nRISKY case diff:\n")
    print(result2["diff"])
