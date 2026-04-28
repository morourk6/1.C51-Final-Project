
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

    print(f"\n{input_path} → {output_path} | {len(df.columns)} columns kept")
    print(f"  Dropped sparse : {sparse or 'none'}")
    print(f"  Dropped named  : {named or 'none'}")
    
    return df


# Call the basic cleaning function and save new files
clean_capacity = clean_csv("capacity.csv", "capacity_new.csv", threshold = 0.25, drop_cols = ["source_id","comment"])
clean_coal = clean_csv("coal.csv", "coal_new.csv", threshold = 0.25, drop_cols = ["source_id","comment", "amount_sold_tonnes"])
clean_commodities = clean_csv("commodities.csv", "commodoties_new.csv", threshold = 0.25, drop_cols = ["source_id","comment", "amount_sold_tonnes","metal_payable_tonnes","mine_processing"])
clean_minerals = clean_csv("minerals.csv", "minerals_new.csv", threshold = 0.25, drop_cols = ["source_id","comment", "amount_sold_tonnes","mine_processing"])
clean_reserves = clean_csv("reserves.csv", "reserves_new.csv", threshold = 0.25, drop_cols = ["source_id","comment"])
clean_waste = clean_csv("waste.csv", "waste_new.csv", threshold = 0.25, drop_cols = ["source_id","comment"])

# changing strings to be numbers so we can do calculations (i.e. reserve back/forward filling)
# reserves
clean_reserves["mineral_value_tonnes"]   = pd.to_numeric(clean_reserves["mineral_value_tonnes"], errors="coerce")
clean_reserves["commodity_value_tonnes"] = pd.to_numeric(clean_reserves["commodity_value_tonnes"], errors="coerce")
clean_reserves["grade_ppm"]              = pd.to_numeric(clean_reserves["grade_ppm"], errors="coerce")

# coal
clean_coal["value_tonnes"]               = pd.to_numeric(clean_coal["value_tonnes"], errors="coerce")

# minerals
clean_minerals["value_tonnes"]           = pd.to_numeric(clean_minerals["value_tonnes"], errors="coerce")

# commodities
clean_commodities["value_tonnes"]        = pd.to_numeric(clean_commodities["value_tonnes"], errors="coerce")
clean_commodities["grade_ppm"]           = pd.to_numeric(clean_commodities["grade_ppm"], errors="coerce")
clean_commodities["recovery_rate"]       = pd.to_numeric(clean_commodities["recovery_rate"], errors="coerce")

# waste
clean_waste["value_tonnes"]              = pd.to_numeric(clean_waste["value_tonnes"], errors="coerce")
clean_waste["total_material_tonnes"]     = pd.to_numeric(clean_waste["total_material_tonnes"], errors="coerce")

# capacity
clean_capacity["value_tpa"]              = pd.to_numeric(clean_capacity["value_tpa"], errors="coerce")

print("Done!")
# Want to be using filename_new after running this cell for future uses

### Back and Forward Fill Data
# Create file paths
# reserves_path = "reserves.csv"
# coal_path     = "coal.csv"
# minerals_path = "minerals.csv"
output_path   = "reserves_filled.csv"

# Add together coal and mineral production files
production = pd.concat([
    clean_coal[clean_coal["type"] == "Coal mined"][["facility_id", "year", "material", "value_tonnes"]],
    clean_minerals[clean_minerals["type"] == "Ore mined"][["facility_id", "year", "material", "value_tonnes"]]
], ignore_index=True)

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

filled_parts = [fill_one_group(g, production)
                for _, g in reserves.groupby(["facility_id", "material"])]
filled_parts = [f for f in filled_parts if not f.empty]

all_filled = pd.concat(filled_parts, ignore_index=True) if filled_parts else pd.DataFrame()
result     = pd.concat([reserves, all_filled], ignore_index=True) if not all_filled.empty else reserves.copy()

result.sort_values(["facility_id", "material", "year"], inplace=True)
result.to_csv(output_path, index=False)

print(f"Original rows : {len(reserves)}")
print(f"Filled rows   : {len(all_filled)}")