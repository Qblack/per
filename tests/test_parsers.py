import csv
import os

import pandas as pd

from per import parsers as sut

import pytest
from faker import Faker


def generate_fake_csv(file_path: str, column_definitions: dict, row_amounts: int = 100, writeheaders=True):
    with open(file_path, "w") as fh:
        writer = csv.DictWriter(fh, fieldnames=column_definitions.keys())
        if writeheaders:
            writer.writeheader()
        for i in range(row_amounts):
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

    file = faker.file_name(extension='.csv')
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

    file = faker.file_name(extension='.csv')
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

    file = faker.file_name(extension='.csv')
    file_path = generate_fake_csv(file, column_definition, writeheaders=True)

    def teardown():
        os.remove(file_path)

    request.addfinalizer(teardown)

    return file_path


class TestParsers:

    def test_parse_american_express_summary_file(self):
        assert False

    def test_parse_rbc_file(self, faker: Faker, rbc_file):
        source = f"RBC-{faker.date()}"

        og_df = pd.read_csv(rbc_file, parse_dates=[1])

        actual = sut.parse_rbc_file(rbc_file, source)

        assert "Account Type" not in actual
        assert "Description 2" not in actual
        assert "CAD$" not in actual
        assert "USD$" not in actual
        assert (actual.Source == source).all()
        assert (actual.Clean == "").all()
        assert (actual.Debit >= 0).all()
        assert (actual.Credit >= 0).all()

        expected_debits = og_df[og_df["CAD$"] < 0]["CAD$"].sum() + og_df.query("`USD$` < 0 and `CAD$` == 0")["USD$"].sum()
        assert expected_debits == -1 * actual[actual.Debit != 0]["Debit"].sum()
        expected_credits = og_df[og_df["CAD$"] > 0]["CAD$"].sum() + og_df.query("`USD$` > 0 and `CAD$` == 0")["USD$"].sum()
        assert expected_credits == actual[actual.Credit != 0]["Credit"].sum()

    def test_parse_td_file(self, faker: Faker, td_file):
        source = f"TD-{faker.date()}"
        actual = sut.parse_td_file(td_file, source)

        assert "Balance" not in actual
        assert (actual.Source == source).all()
        assert (actual.Clean == "").all()

    def test_parse_scotia_file(self, faker, scotia_file):
        source = f"Scotia-{faker.date()}"

        og_df = pd.read_csv(scotia_file, header=None, names=["Date", "Place", "Amount"], parse_dates=[0])

        actual = sut.parse_scotia_file(scotia_file, source)

        assert "Amount" not in actual
        assert (actual.Source == source).all()
        assert (actual.Clean == "").all()
        assert (actual.Debit >= 0).all()
        assert (actual.Credit >= 0).all()
        assert og_df[og_df.Amount < 0]["Amount"].sum() == -1 * actual[actual.Debit != 0]["Debit"].sum()
        assert og_df[og_df.Amount > 0]["Amount"].sum() == actual[actual.Credit != 0]["Credit"].sum()





