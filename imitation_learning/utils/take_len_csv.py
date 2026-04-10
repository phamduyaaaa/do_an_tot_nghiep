"""Module to count the number of rows in a CSV dataset."""

import csv
import sys


def count_csv_rows(file_path: str) -> int:
    """Counts the total number of lines in a given CSV file.

    Args:
        file_path: The path to the CSV file.

    Returns:
        The total number of rows found in the file.
    """
    try:
        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            return sum(1 for _ in reader)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)


def main() -> None:
    """Main execution function."""
    csv_file = "dataset.csv"
    line_count = count_csv_rows(csv_file)

    print(f"Line: {csv_file}: {line_count}")


if __name__ == "__main__":
    main()
