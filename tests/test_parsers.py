import csv
import math
import os
import shutil
from pathlib import Path

import pandas as pd
import polars as pl
import pytest
from faker import Faker

from per import parsers as sut
from tests import TEST_DATA_DIR


def generate_fake_csv(
    file_path: str, column_definitions: dict, writeheaders: bool, row_amounts: int = 100  # noqa: FBT001
):
    with open(file_path, "w") as fh:
        writer = csv.DictWriter(fh, fieldnames=column_definitions.keys())
        if writeheaders:
            writer.writeheader()
        for _ in range(row_amounts):
            row = {k: v() for k, v in column_definitions.items()}
            writer.writerow(row)

    return file_path


@pytest.fixture()
def td_file(request, faker):
    column_definition = {
        "Date": faker.date,
        "Place": faker.company,
        "Debit": faker.pyfloat,
        "Credit": faker.pyfloat,
        "Balance": faker.pyfloat,
    }

    file = faker.file_name(extension="csv")
    file_path = generate_fake_csv(file, column_definition, writeheaders=False)

    def teardown():
        os.remove(file_path)

    request.addfinalizer(teardown)

    return file_path


@pytest.fixture()
def scotia_file(request, faker):
    column_definition = {
        "Date": faker.date,
        "Place": faker.company,
        "Amount": faker.pyfloat,
    }

    file = faker.file_name(extension="csv")
    file_path = generate_fake_csv(file, column_definition, writeheaders=False)

    def teardown():
        os.remove(file_path)

    request.addfinalizer(teardown)

    return file_path


@pytest.fixture()
def rbc_file(request, faker: Faker):
    column_definition = {
        "Account Type": faker.pystr,
        "Transaction Date": faker.date,
        "Description 1": faker.company,
        "Description 2": faker.pystr,
        "CAD$": faker.pyfloat,
        "USD$": faker.pyfloat,
    }

    file = faker.file_name(extension="csv")
    file_path = generate_fake_csv(file, column_definition, writeheaders=True)

    def teardown():
        os.remove(file_path)

    request.addfinalizer(teardown)

    return file_path


def generate_amex_file(request, faker: Faker):
    original = Path(TEST_DATA_DIR, "American-Express-2023.xls")
    file_name = "wusers_" + faker.file_name(extension="xls")
    file_path = Path(TEST_DATA_DIR, file_name)
    shutil.copyfile(original, file_path)

    def teardown():
        os.remove(file_path)

    request.addfinalizer(teardown)

    return file_path


def generate_userless_amex_file(request, faker: Faker):
    original = Path(TEST_DATA_DIR, "American-Express-2023-Userless.xls")
    file_name = "userless_" + faker.file_name(extension="xls")
    file_path = Path(TEST_DATA_DIR, file_name)
    shutil.copyfile(original, file_path)

    def teardown():
        os.remove(file_path)

    request.addfinalizer(teardown)

    return file_path


class TestParsers:
    def test_parse_american_express_summary_file(self, request, faker: Faker):
        amex_file = generate_amex_file(request, faker)
        source = f"Amex-{faker.date()}"
        expected = pd.read_excel(
            amex_file, skiprows=12, parse_dates=[0], header=None, names=["Date", "Place", "Blank", "User", "Amount"]
        )

        actual = sut.parse_american_express_summary_file(amex_file, source)

        assert "Amount" not in actual
        assert "Blank" not in actual

        def currency_to_float(x):
            return float(x.replace("$", "").replace(",", ""))

        expected = expected.Amount.apply(currency_to_float)
        expected_debits = expected[expected > 0].sum()
        expected_credits = expected[expected < 0].sum()
        assert math.isclose(expected_debits, actual["Debit"].sum())
        assert math.isclose(-1 * expected_credits, actual["Credit"].sum())

    def test_parse_american_express_summary_file_no_user_still_works(self, request, faker: Faker):
        userless_amex_file = generate_userless_amex_file(request, faker)

        source = f"Amex-{faker.date()}"
        expected = pd.read_excel(
            userless_amex_file,
            sheet_name="Summary",
            skiprows=12,
            parse_dates=[0],
            header=None,
            names=["Date", "Place", "Blank", "Amount"],
        )

        actual = sut.parse_american_express_summary_file(userless_amex_file, source)

        assert "Amount" not in actual
        assert "Blank" not in actual

        def currency_to_float(x):
            return float(x.replace("$", "").replace(",", ""))

        expected = expected.Amount.apply(currency_to_float)
        expected_debits = expected[expected > 0].sum()
        expected_credits = expected[expected < 0].sum()
        assert math.isclose(expected_debits, actual["Debit"].sum())
        assert math.isclose(expected_credits, -1 * actual["Credit"].sum())

    def test_parse_rbc_file(self, faker: Faker, rbc_file):
        source = f"RBC-{faker.date()}"

        og_df = pd.read_csv(rbc_file, parse_dates=[1])

        actual = sut.parse_rbc_file(rbc_file, source)

        assert "Account Type" not in actual
        assert "Description 2" not in actual
        assert "CAD$" not in actual
        assert "USD$" not in actual
        assert "Amount" not in actual

        assert (actual["Source"] == source).all()
        assert (actual["Clean"] == "").all()
        assert (actual["Debit"] >= 0).all()
        assert (actual["Credit"] >= 0).all()

        expected_debits = (
            og_df[og_df["CAD$"] < 0]["CAD$"].sum() + og_df.query("`USD$` < 0 and `CAD$` == 0")["USD$"].sum()
        )
        assert expected_debits == -1 * actual["Debit"].sum()
        expected_credits = (
            og_df[og_df["CAD$"] > 0]["CAD$"].sum() + og_df.query("`USD$` > 0 and `CAD$` == 0")["USD$"].sum()
        )
        assert expected_credits == actual["Credit"].sum()

    def test_parse_td_file(self, faker: Faker, td_file):
        source = f"TD-{faker.date()}"
        actual = sut.parse_td_file(td_file, source)
        og_df = pd.read_csv(
            td_file, header=None, names=["Date", "Place", "Debit", "Credit", "Balance"], parse_dates=[0]
        )

        assert "Balance" not in actual
        assert actual.filter(pl.col("Source") == source).shape[0] == len(og_df)
        assert actual.filter(pl.col("Clean") == "").shape[0] == len(og_df)

    def test_parse_scotia_file(self, faker, scotia_file):
        source = f"Scotia-{faker.date()}"

        og_df = pd.read_csv(scotia_file, header=None, names=["Date", "Place", "Amount"], parse_dates=[0])

        actual = sut.parse_scotia_file(scotia_file, source)

        assert "Amount" not in actual
        assert actual.filter(pl.col("Debit") >= 0).shape[0] == len(og_df)
        assert actual.filter(pl.col("Credit") >= 0).shape[0] == len(og_df)
        assert actual.filter(pl.col("Source") == source).shape[0] == len(og_df)
        assert actual.filter(pl.col("Clean") == "").shape[0] == len(og_df)

        assert math.isclose(og_df[og_df.Amount < 0]["Amount"].sum(), -1 * actual["Debit"].sum())
        assert math.isclose(og_df[og_df.Amount > 0]["Amount"].sum(), actual["Credit"].sum())
