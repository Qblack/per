from datetime import datetime
from pathlib import Path

import pandas as pd
import polars as pl


def parse_american_express_summary_file(file_path: str | Path, source: str = "American Express") -> pl.DataFrame:
    # TODO check if user is actually presents

    df = pd.read_excel(file_path, "Summary", skiprows=11)

    columns_to_keep = ["Date", "Description", "Amount"]
    columns_to_remove = [col for col in df.columns if col not in columns_to_keep]
    df = df.drop(columns=columns_to_remove)

    df = pl.from_dataframe(df)
    # FYI User column is not present in all files

    # if df["Amount"].is_null().all():
    #     df = df.drop("Amount")
    #     df = df.rename(columns={"User": "Amount"})

    def fix_amex(row):
        try:
            row["Amount"] = float(row["Amount"].replace("$", "").replace(",", ""))
        except (ValueError, AttributeError):
            row["Amount"] = float(row["Amount"])

        if row["Amount"] > 0:
            row["Debit"] = row["Amount"]
        else:
            row["Credit"] = row["Amount"] * -1
        row["Date"] = datetime.strptime(row["Date"], "%d %b %Y").replace(tzinfo=None)  # noqa DTZ007
        return row

    df = df.with_columns(
        pl.col("Date").str.to_date("%d %b %Y").alias("Date"),
        pl.col("Description").alias("Place"),
        pl.col("Amount").str.replace(r"\$", "").str.replace(",", "").cast(pl.Float64).alias("Amount"),
    )

    df = df.with_columns(
        pl.when(pl.col("Amount") < 0).then(-pl.col("Amount")).otherwise(0).alias("Credit"),
        pl.when(pl.col("Amount") > 0).then(pl.col("Amount")).otherwise(0).alias("Debit"),
        pl.lit(source).alias("Source"),
        pl.lit("").alias("Clean"),
    )

    df = df.drop("Amount")
    return df


def parse_rbc_file(file_path: str | Path, source: str) -> pl.DataFrame:
    df = pl.read_csv(file_path, use_pyarrow=True)
    # , names=['Account Type', 'Date', 'Place', 'Place 2', 'Amount', 'USD$']
    # Merge cad and usd columns
    df = df.with_columns(
        pl.when(pl.col("CAD$").is_null()).then(pl.col("USD$")).otherwise(pl.col("CAD$")).alias("Amount")
    )

    df = df.with_columns(
        pl.col("Transaction Date").alias("Date"),
        pl.col("Description 1").alias("Place"),
        pl.when(pl.col("Amount") > 0).then(pl.col("Amount")).otherwise(0).alias("Credit"),
        pl.when(pl.col("Amount") < 0).then(-pl.col("Amount")).otherwise(0).alias("Debit"),
        pl.lit(source).alias("Source"),
        pl.lit("").alias("Clean"),
    )

    df = df.drop("Amount")
    df = df.drop("Account Type")
    df = df.drop("Description 2")
    df = df.drop("CAD$")
    df = df.drop("USD$")

    return df


def parse_td_file(file_path: str | Path, source: str) -> pl.DataFrame:
    df = pl.read_csv(
        file_path, has_header=False, new_columns=["Date", "Place", "Debit", "Credit", "Balance"], use_pyarrow=True
    )
    df = df.drop("Balance")
    df = df.with_columns(pl.lit(source).alias("Source"), pl.lit("").alias("Clean"))
    return df


def parse_scotia_file(file_path: str | Path, source: str) -> pl.DataFrame:
    df = pl.read_csv(file_path, has_header=False, new_columns=["Date", "Place", "Amount"], use_pyarrow=True)
    df = df.with_columns(
        pl.when(pl.col("Amount") < 0).then(-pl.col("Amount")).otherwise(0).alias("Debit"),
        pl.when(pl.col("Amount") > 0).then(pl.col("Amount")).otherwise(0).alias("Credit"),
        pl.lit(source).alias("Source"),
        pl.lit("").alias("Clean"),
    )

    df = df.drop("Amount")
    return df
