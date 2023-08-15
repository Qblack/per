import logging
import os

import pandas as pd

from per import categoryinator, cleaninator, parsers

LOG = logging.getLogger(__name__)


def process_statements(source_dir, category_map, cleanup_map):
    expenses = []

    for file_name in os.listdir(source_dir):
        file_path = os.path.join(source_dir, file_name)
        df = pd.DataFrame()
        if "scotia-visa" in file_name.lower():
            df = parsers.parse_scotia_file(file_path, "SCOTIA-VISA")
        elif "td-visa" in file_name.lower():
            df = parsers.parse_td_file(file_path, "TD-VISA")
        elif "td-cheq" in file_name.lower():
            df = parsers.parse_td_file(file_path, "TD-CHEQ")
        elif "american-express" in file_name.lower():
            df = parsers.parse_american_express_summary_file(file_path, "AMERICAN-EXPRESS")
        elif "rbc" in file_name.lower():
            df = parsers.parse_rbc_file(file_path, "RBC-VISA")
        LOG.info("Parsed: %s" % file_name)
        expenses.append(df)
    LOG.info("Parsing complete - Cleaning")
    result = pd.concat(expenses)
    result.fillna(0, inplace=True)
    result.drop_duplicates(inplace=True)
    result["Category"] = ""
    LOG.info("Categorizing")
    result = categoryinator.categorize(result, category_map)
    LOG.info("Cleaning")
    result = cleaninator.add_clean_values(result, cleanup_map)

    def add_month(row):
        row["Month"] = row["Date"].month
        row["Year"] = row["Date"].year
        row["Day"] = row["Date"].day
        return row

    LOG.info("Adding month, year, day")
    result = result.apply(add_month, axis=1)
    cols = result.columns.tolist()
    cols = cols[0:1] + [cols[-1]] + cols[1:-1]
    cols = cols[0:-2] + [cols[-1]] + [cols[-2]]
    df = result[cols]
    LOG.info("Splitting categorized and uncategorized")
    uncategorized_transactions = df[df.Category == ""]
    categorized_transactions = df[df.Category != ""]
    uncategorized_transactions = uncategorized_transactions.sort_values(by=["Date"], ascending=False)
    return categorized_transactions, uncategorized_transactions


def write_to_excel(excel_path, df, sheet_name, index=False, columns=None):  # noqa FBT002
    with pd.ExcelWriter(excel_path, mode="a", engine="openpyxl", if_sheet_exists="overlay") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=index, columns=columns)
    return excel_path
