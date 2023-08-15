import math
from pathlib import Path

import pandas as pd
import yaml

MIN_BUS = 70

MAX_BUS = 100


def create_category_map(category_file: str | Path):
    category_map = []
    with open(category_file) as fh:
        cats = yaml.safe_load(fh)
        for category, comps in cats.items():
            for comp in comps:
                cat_map = {"like": comp, "category": category}
                category_map.append(cat_map)
    return category_map


def categorize(df: pd.DataFrame, category_map: dict[str, list[str]]):
    def categorize_row(row, categorize_map):
        for mapping in categorize_map:
            like = mapping["like"]
            category = mapping["category"]
            # Basically used to have to buy bus passes at shoppers for a flat rate no tax.
            if (
                row["Debit"] == math.floor(row["Debit"])
                and MAX_BUS > row["Debit"] > MIN_BUS
                and ("SHOPPERS" in row["Place"] or "RMOW GRT" in row["Place"])
            ):
                row["Category"] = "BUS PASS"
            elif like.lower() in row["Place"].lower():
                row["Category"] = category
                row["Clean"] = like.upper()
                break
        return row

    df = df.apply(categorize_row, axis=1, args=(category_map,))
    return df
