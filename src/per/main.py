import argparse
import logging
import os
import sys

from per import categoryinator, cleaninator, file_manager

LOG = logging.getLogger(__name__)


def main(output_file_path, source_dir, category_file_path, clean_file_path):
    category_map = categoryinator.create_category_map(category_file_path)
    cleanup_map = cleaninator.create_cleanup_map(clean_file_path)

    LOG.info("Processing statements")
    categorized_transactions, uncategorized_transactions = file_manager.process_statements(
        source_dir, category_map, cleanup_map
    )
    LOG.info("Writing uncategorized to excel")
    uncategorized_transactions.to_csv("output/uncategorized.csv", index=False)
    LOG.info("Writing categorized to excel")
    categorized_transactions.to_csv("output/categorized.csv", index=False)
    LOG.info("Updating Categorized excel file")
    file_manager.write_to_excel(
        output_file_path,
        categorized_transactions,
        "Expenses",
        columns=["Date", "Day", "Place", "Debit", "Credit", "Source", "Category", "Year", "Month", "Clean"],
    )
    LOG.info("Updating Uncategorized excel file")
    file_manager.write_to_excel(output_file_path, uncategorized_transactions, "Uncategorized")

    return categorized_transactions, uncategorized_transactions


def get_source_dir():
    current_dir = os.path.split(os.path.abspath(__file__))[0]

    while os.path.exists(current_dir) and not os.path.exists(os.path.join(current_dir, "Files")):
        current_dir = os.path.split(current_dir)[0]
    return os.path.join(current_dir, "Files")


def get_output_file_name(source_dir, default_file_name="BudgetAndTracking.xlsx"):
    out_put_file_name = input(f"What file would you like to update? (Default) {default_file_name}:").strip()
    if len(out_put_file_name) == 0:
        out_put_file_name = default_file_name
    if not out_put_file_name.endswith(".xlsx"):
        out_put_file_name += ".xlsx"
    if os.path.exists(out_put_file_name):
        return out_put_file_name
    else:
        return os.path.join(source_dir, out_put_file_name)


if __name__ == "__main__":
    # TODO try out click maybe?
    root_logger = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    parser = argparse.ArgumentParser(description="Categorize Expenses")
    parser.add_argument("--source_dir", type=str, help="Folder containing files to import")
    parser.add_argument(
        "--destination_file", help="Name of Excel file to generate", default="output/BudgetAndTracking-Q.xlsx"
    )

    # TODO figure out how to pass these nicely
    categories_file_path = r"C:\Users\Q\Code\per\categories.yml"
    cleanup_file_path = r"C:\Users\Q\Code\per\place_mappings.yml"
    args = parser.parse_args()

    SOURCE_DIR = args.source_dir or get_source_dir()
    OUTPUT_FILE_PATH = args.destination_file or get_output_file_name(os.path.split(SOURCE_DIR)[0])
    LOG.info(args)

    main(OUTPUT_FILE_PATH, SOURCE_DIR, categories_file_path, cleanup_file_path)
