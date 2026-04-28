
import os
import geopandas as gpd
import fiona
import pandas as pd

### Function to take out columns with no data, data less than 25% filled, and specific named columns
def clean_csv(input_path, output_path, threshold=0.25, drop_cols=None):
    df = pd.read_csv(input_path, dtype=str).replace(r"^\s*$", pd.NA, regex=True)

    sparse  = df.columns[df.notna().mean() < threshold].tolist()
    named   = [c for c in (drop_cols or []) if c in df.columns]
    missing = [c for c in (drop_cols or []) if c not in df.columns]

    df.drop(columns=list(dict.fromkeys(sparse + named)), inplace=True)
    df.to_csv(output_path, index=False)
    return df

    print(f"\n{input_path} → {output_path} | {len(df.columns)} columns kept")
    print(f"  Dropped sparse : {sparse or 'none'}")
    print(f"  Dropped named  : {named or 'none'}")


### Back and Forward Fill Data
# Create file paths
reserves_path = "reserves.csv"
coal_path     = "coal.csv"
minerals_path = "minerals.csv"
output_path   = "reserves_filled.csv"

# Add together coal and mineral production files
def load_production(coal_path, minerals_path):
    coal     = pd.read_csv(coal_path)
    minerals = pd.read_csv(minerals_path)
    coal     = coal[coal["type"] == "Coal mined"][["facility_id", "year", "material", "value_tonnes"]]
    minerals = minerals[minerals["type"] == "Ore mined"][["facility_id", "year", "material", "value_tonnes"]]
    return pd.concat([coal, minerals], ignore_index=True)

# Backfill and forward fill from reserve values given
# If 2 values given, assume new prospecting at later date, and only forward fill from this point
def fill_one_group(known_rows, production):
    fid, mat   = known_rows["facility_id"].iloc[0], known_rows["material"].iloc[0]
    anchors    = dict(zip(known_rows["year"], known_rows["mineral_value_tonnes"]))
    prod       = production[(production["facility_id"] == fid) & (production["material"] == mat)]
    prod       = prod.set_index("year")["value_tonnes"].to_dict()
    if not prod:
        return pd.DataFrame()

    anchor_years = sorted(anchors)
    estimates    = {}

    for i, ay in enumerate(anchor_years):
        av          = anchors[ay]
        next_anchor = anchor_years[i + 1] if i + 1 < len(anchor_years) else None
        if pd.isna(av):
            continue

        val = av
        for y in sorted(y for y in prod if y > ay):
            if next_anchor and y >= next_anchor:
                break
            val -= prod[y]
            estimates[y] = val

        if i == 0:
            val = av
            for y in sorted((y for y in prod if y < ay), reverse=True):
                val += prod[y]
                estimates[y] = val

    template = known_rows.iloc[0].to_dict()
    return pd.DataFrame([
        {**template, "year": y, "mineral_value_tonnes": v,
         "commodity_value_tonnes": None, "grade_ppm": None,
         "source_id": "filled", "comment": None}
        for y, v in estimates.items() if y not in anchors
    ])

# Run the code and recieve new CSV file
reserves   = pd.read_csv(reserves_path)
production = load_production(coal_path, minerals_path)

filled_parts = [fill_one_group(g, production)
                for _, g in reserves.groupby(["facility_id", "material"])]
filled_parts = [f for f in filled_parts if not f.empty]

all_filled = pd.concat(filled_parts, ignore_index=True) if filled_parts else pd.DataFrame()
result     = pd.concat([reserves, all_filled], ignore_index=True) if not all_filled.empty else reserves.copy()

result.sort_values(["facility_id", "material", "year"], inplace=True)
result.to_csv(output_path, index=False)

print(f"Original rows : {len(reserves)}")
print(f"Filled rows   : {len(all_filled)}")