import pandas as pd
import plotly.graph_objects as go
import colorsys
import os


# ─────────────────────────────────────────────────
# STEP 1 -- LOAD THE FILE
# ─────────────────────────────────────────────────

def load_data():
    while True:
        file_path = input("Enter the path to your Excel or CSV file: ").strip()
        try:
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path, header=0)
                if any("Unnamed" in str(col) or "Table" in str(col) for col in df.columns):
                    df = pd.read_excel(file_path, header=1)
            print(f"\nLoaded {len(df)} rows successfully")
            return df
        except FileNotFoundError:
            print("\nFile not found. Please check the path and try again.")
        except Exception as e:
            print(f"\nUnable to load the file: {e}")
            print("Please check that the file is a valid Excel or CSV file and try again.")


# ─────────────────────────────────────────────────
# STEP 2 -- CARDINALITY DETECTION
# ─────────────────────────────────────────────────

def analyze_columns(df):
    recommended     = []
    not_recommended = []
    date_columns    = []

    date_keywords = ["_date", "_datetime", "_timestamp", "date_", "datetime_"]

    for col in df.columns:
        total_rows   = len(df)
        unique_count = df[col].nunique()
        unique_pct   = unique_count / total_rows

        # Check if column is already a datetime type
        # OR if the column name contains a strictly date specific word
        if pd.api.types.is_datetime64_any_dtype(df[col]) or \
           any(keyword in col.lower() for keyword in date_keywords):
            date_columns.append(col)
            continue

        # Check if column is text based
        if df[col].dtype == object:
            if unique_pct > 0.95:
                not_recommended.append((col, "too many unique values -- likely an identifier"))
            else:
                recommended.append(col)

        # Check if column is numeric
        elif pd.api.types.is_numeric_dtype(df[col]):
            if unique_count <= 20:
                recommended.append(col)
            else:
                not_recommended.append((col, "continuous number -- too many unique values"))

    return recommended, not_recommended, date_columns


def display_columns(df, recommended, not_recommended, date_columns):
    print("\n─────────────────────────────────────────────────")
    print("COLUMN ANALYSIS")
    print("─────────────────────────────────────────────────")

    print("\nRECOMMENDED FOR SANKEY STAGES:")
    if recommended:
        for i, col in enumerate(recommended, 1):
            print(f"   {i}. {col}")
    else:
        print("   None found -- all columns appear continuous or unique")

    if date_columns:
        print("\nDATE COLUMNS (can be derived into year for use as a stage):")
        for col in date_columns:
            print(f"   - {col}")

    print("\nNOT RECOMMENDED (usable but may produce messy results):")
    if not_recommended:
        for col, reason in not_recommended:
            print(f"   - {col}  ({reason})")
    else:
        print("   None")

    print("\nALL AVAILABLE COLUMNS:")
    for i, col in enumerate(df.columns, 1):
        tag = ""
        if col in recommended:
            tag = "  <-- recommended"
        elif col in [c for c, _ in not_recommended]:
            tag = "  <-- not recommended"
        elif col in date_columns:
            tag = "  <-- date column"
        print(f"   {i}. {col}{tag}")

    print("─────────────────────────────────────────────────")


# ─────────────────────────────────────────────────
# STEP 3 -- OPTIONAL DATE TO YEAR DERIVATION
# ─────────────────────────────────────────────────

def derive_year(df, date_columns):
    if not date_columns:
        return df

    print("\nDo you have a date column you want to group by year? (yes/no)")
    choice = input(": ").strip().lower()

    while True:
        if choice == "yes":
            while True:
                print("\nWhich column contains the date?")
                date_col = input(": ").strip()
                if date_col in df.columns:
                    break
                else:
                    print(f"\nColumn '{date_col}' not found. Please type the column name exactly as it appears above.")

            df[date_col]    = pd.to_datetime(df[date_col])
            derived_col     = f"Derived Year ({date_col})"
            df[derived_col] = df[date_col].dt.year.astype(str)
            print(f"\nYear column created successfully from {date_col}")

        elif choice == "no":
            break
        else:
            print("\nInvalid input. Please type yes or no.")
            print("\nDo you have a date column you want to group by year? (yes/no)")
            choice = input(": ").strip().lower()
            continue

        print("\nDo you have another date column you want to group by year? (yes/no)")
        choice = input(": ").strip().lower()
        if choice != "yes":
            break

    return df


# ─────────────────────────────────────────────────
# STEP 4 -- GET USER INPUTS
# ─────────────────────────────────────────────────

def get_user_inputs(df, recommended, not_recommended, date_columns):
    print("\nHow many stages do you want in your Sankey chart? (2-5)")
    print("   2 -- two stages   (example: Region --> Product Category)")
    print("   3 -- three stages (example: Region --> Product Category --> Status)")
    print("   4 -- four stages  (example: Region --> Department --> Product Category --> Status)")
    print("   5 -- five stages  (example: Region --> Department --> Job Title --> Product Category --> Status)")
    print("\nType a number between 2 and 5:")

    while True:
        try:
            stages = int(input(": ").strip())
            if 2 <= stages <= 5:
                break
            else:
                print("Please enter a number between 2 and 5.")
        except ValueError:
            print("Invalid input. Please type a number between 2 and 5.")

    print("\nAll available columns (recommended columns are flagged):")
    for i, col in enumerate(df.columns, 1):
        tag = ""
        if col in recommended:
            tag = "  <-- recommended"
        elif col in [c for c, _ in not_recommended]:
            tag = "  <-- not recommended"
        elif col in date_columns:
            tag = "  <-- date column"
        print(f"   {i}. {col}{tag}")

    selected_cols = []

    for i in range(stages):
        if i == 0:
            label = "Stage 1 (leftmost)"
        elif i == stages - 1:
            label = f"Stage {i + 1} (rightmost)"
        else:
            label = f"Stage {i + 1}"

        while True:
            print(f"\nWhich column is your {label}?")
            col = input(": ").strip()
            if col in df.columns:
                if col in [c for c, _ in not_recommended]:
                    print(f"\nNote: '{col}' is not recommended as a Sankey stage but you can still use it.")
                    print("Do you want to proceed with this column? (yes/no)")
                    confirm = input(": ").strip().lower()
                    if confirm == "yes":
                        selected_cols.append(col)
                        break
                    else:
                        continue
                else:
                    selected_cols.append(col)
                    break
            else:
                print(f"\nColumn '{col}' not found. Please type the column name exactly as it appears above.")

    print("\nHow do you want to calculate the flow values in your Sankey chart?")
    print("   count  -- counts how many rows fall into each combination")
    print("            (example: how many employees are in each department per region)")
    print("   column -- sums an existing number column you already have")
    print("            (example: total revenue per product category per region)")
    print("\nType count or column:")

    while True:
        value_choice = input(": ").strip().lower()
        if value_choice in ["count", "column"]:
            break
        else:
            print("Invalid input. Please type count or column.")

    value_col = None
    if value_choice == "column":
        while True:
            print("\nWhich column contains your values?")
            value_col = input(": ").strip()
            if value_col in df.columns:
                break
            else:
                print(f"\nColumn '{value_col}' not found. Please type the column name exactly as it appears above.")

    print("\nWhat would you like to title your Sankey chart?")
    chart_title = input(": ").strip()
    if not chart_title:
        chart_title = "Sankey Chart"

    print("\nWhat would you like to name your output file? (do not include .html)")
    output_name = input(": ").strip()
    if not output_name:
        output_name = "sankey_chart"
    output_name = output_name + ".html"

    return stages, selected_cols, value_choice, value_col, chart_title, output_name


# ─────────────────────────────────────────────────
# STEP 5 -- AGGREGATE INTO SANKEY FORMAT
# ─────────────────────────────────────────────────

def aggregate_data(df, selected_cols, value_choice, value_col):

    def group(df, col_a, col_b):
        if value_choice == "count":
            return (
                df.groupby([col_a, col_b])
                .size()
                .reset_index(name="Count")
            ), "Count"
        else:
            return (
                df.groupby([col_a, col_b])[value_col]
                .sum()
                .reset_index()
            ), value_col

    flows = []
    for i in range(len(selected_cols) - 1):
        grouped, val_col = group(df, selected_cols[i], selected_cols[i + 1])
        flows.append((grouped, selected_cols[i], selected_cols[i + 1], val_col))

    total_flows = sum(len(f[0]) for f in flows)
    print(f"\nAggregated into {total_flows} unique flows")
    return flows, val_col


# ─────────────────────────────────────────────────
# STEP 6 -- BUILD AND EXPORT THE SANKEY CHART
# ─────────────────────────────────────────────────

def generate_colors(n):
    colors = []
    for i in range(n):
        hue = i / n
        r, g, b = colorsys.hsv_to_rgb(hue, 0.6, 0.85)
        colors.append(
            f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        )
    return colors


def hex_to_rgba(hex_color, opacity=0.4):
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{opacity})"


def build_sankey(flows, chart_title, output_name):
    all_labels = []
    for grouped, src, tgt, val in flows:
        for label in grouped[src].unique().tolist() + grouped[tgt].unique().tolist():
            if label not in all_labels:
                all_labels.append(label)

    label_index    = {label: i for i, label in enumerate(all_labels)}
    source_indices = []
    target_indices = []
    values         = []

    for grouped, src, tgt, val in flows:
        source_indices += [label_index[s] for s in grouped[src]]
        target_indices += [label_index[t] for t in grouped[tgt]]
        values         += grouped[val].tolist()

    node_colors = generate_colors(len(all_labels))
    link_colors = [hex_to_rgba(node_colors[s]) for s in source_indices]

    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20,
            thickness=30,
            line=dict(color="white", width=0.5),
            label=all_labels,
            color=node_colors
        ),
        link=dict(
            source=source_indices,
            target=target_indices,
            value=values,
            color=link_colors
        )
    )])

    fig.update_layout(
        title=dict(
            text=chart_title,
            font=dict(size=20)
        ),
        font=dict(size=14),
        height=600
    )

    script_dir  = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, output_name)
    fig.write_html(output_file)
    print(f"\nDone. Open {output_file} in your browser.")


# ─────────────────────────────────────────────────
# MAIN -- Runs everything in order
# ─────────────────────────────────────────────────

def main():
    print("─────────────────────────────────────────────────")
    print("SANKEY CHART GENERATOR")
    print("─────────────────────────────────────────────────")
    print("Before you begin, please note:")
    print("")
    print("   1. Sankey stages must be categorical columns")
    print("      (example: year, bucket, department, region)")
    print("      Avoid using columns with unique or continuous")
    print("      numbers like IDs, prices, or lag days as stages.")
    print("")
    print("   2. All inputs are case sensitive.")
    print("      Type column names exactly as they appear")
    print("      in the available columns list.")
    print("─────────────────────────────────────────────────")
    print("")

    df                                                                   = load_data()
    recommended, not_recommended, date_columns                           = analyze_columns(df)
    display_columns(df, recommended, not_recommended, date_columns)
    df                                                                   = derive_year(df, date_columns)
    recommended, not_recommended, date_columns                           = analyze_columns(df)
    stages, selected_cols, value_choice, value_col, chart_title, output_name = get_user_inputs(df, recommended, not_recommended, date_columns)
    flows, value_col                                                     = aggregate_data(df, selected_cols, value_choice, value_col)
    build_sankey(flows, chart_title, output_name)

if __name__ == "__main__":
    main()
