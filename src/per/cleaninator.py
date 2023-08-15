import pandas as pd
import yaml


def create_cleanup_map(cleanup_mapping_file):
    cleanup_map = []
    with open(cleanup_mapping_file) as fh:
        cats = yaml.safe_load(fh)
        for target, matches in cats.items():
            for comp in matches:
                cat_map = {"like": comp, "target": target}
                cleanup_map.append(cat_map)
    return cleanup_map


def add_clean_values(df: pd.DataFrame, cleanup_map: dict[str, list[str]]):
    def cleanup_row(row, clean_up_map):
        for mapping in clean_up_map:
            like = mapping["like"]
            if like.upper() in row["Place"].upper():
                row["Clean"] = mapping["target"]
                break
        return row

    df = df.apply(cleanup_row, axis=1, args=(cleanup_map,))
    return df
