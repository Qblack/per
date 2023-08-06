from pathlib import Path

import pandas as pd
import pendulum


def parse_american_express_summary_file(file_path: str, source: str = "American Express"):
    # TODO check if user is actually presents
    # read_csv_options = {
    #     "has_headers": False,
    #     "new_columns": ["Date", "Place", "Blank", "User", "Amount"],
    #     "skip_rows": 12
    # }
    df = pd.read_excel(file_path, sheet_name="Summary", headers=False,
                       names=["Date", "Place", "Blank", "User", "Amount"], skiprows=12)
    df["Debit"] = 0
    df["Credit"] = 0
    df["Source"] = source
    df["Clean"] = ""

    def fix_amex(row):
        try:
            row["Amount"] = float(row["Amount"].replace("$", "").replace(",", ""))
        except (ValueError, AttributeError):
            row["Amount"] = float(row["Amount"])

        if row["Amount"] > 0:
            row["Debit"] = row["Amount"]
        else:
            row["Credit"] = row["Amount"] * -1
        row["Date"] = pendulum.from_format(row["Date"], "%d %b %Y")
        return row

    df = df.apply(fix_amex, axix=1)
    df = df.drop("Amount", "Blank")
    return df


def parse_rbc_file(file_path: str | Path, source: str) -> pd.DataFrame:
    df = pd.read_csv(file_path, parse_dates=[1])
    # , names=['Account Type', 'Date', 'Place', 'Place 2', 'Amount', 'USD$']
    df = df.rename(columns={"Transaction Date": "Date", "Description 1": "Place"})

    df["Debit"] = 0
    df["Credit"] = 0
    df["Source"] = source
    df["Clean"] = ""

    def fix_rbc(row):
        value = row["CAD$"] or row["USD$"]
        if value < 0:
            row["Debit"] = value * -1
        else:
            row["Credit"] = value
        return row

    df = df.apply(fix_rbc, axis=1)
    del df["Account Type"]
    del df["Description 2"]
    del df["CAD$"]
    del df["USD$"]
    return df


def parse_td_file(file_path: str | Path, source: str) -> pd.DataFrame:
    df = pd.read_csv(file_path, header=None, names=["Date", "Place", "Debit", "Credit", "Balance"], parse_dates=[0])
    del df["Balance"]
    df["Source"] = source
    df["Clean"] = ""
    return df


def parse_scotia_file(file_path: str | Path, source: str) -> pd.DataFrame:
    df = pd.read_csv(file_path, header=None, names=["Date", "Place", "Amount"], parse_dates=[0])
    df["Debit"] = 0
    df["Credit"] = 0
    df["Source"] = source
    df["Clean"] = ""

    def fix_scotia(row):
        if row["Amount"] < 0:
            row["Debit"] = row["Amount"] * -1
        else:
            row["Credit"] = row["Amount"]
        return row

    df = df.apply(fix_scotia, axis=1)
    del df["Amount"]
    return df
