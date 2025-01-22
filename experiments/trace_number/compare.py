import pandas as pd
import sys
import numpy as np
import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="Compare two trace files")
    parser.add_argument("file1", help="First input file (should be cryo)")
    parser.add_argument("file2", help="Second input file (should be trace_number)")
    return parser.parse_args()


def count_number_of_traces(file1, file2):
    # Load the two files and replace empty strings with NaN
    file1_df = pd.read_csv(file1).replace(r"^\s*$", np.nan, regex=True)
    file2_df = pd.read_csv(file2).replace(r"^\s*$", np.nan, regex=True)

    file1_df["action_to"] = file1_df["action_to"].fillna(file1_df["result_address"])
    file2_df["trace_address"] = file2_df["trace_address"].str.replace(",", "_")

    # Rename columns for comparison
    file1_renamed = file1_df.rename(
        columns={
            "transaction_hash": "tx_hash",
            "trace_address": "trace_addr",
            "action_from": "from",
            "action_to": "to",
        }
    )

    file2_renamed = file2_df.rename(
        columns={
            "transaction_hash": "tx_hash",
            "trace_address": "trace_addr",
            "from_address": "from",
            "to_address": "to",
        }
    )

    print(f"Total rows in file1: {len(file1_renamed)}")
    print(f"Total rows in file2: {len(file2_renamed)}")

    return file1_renamed, file2_renamed


def count_differences(file1_renamed, file2_renamed):
    file1_counts = (
        file1_renamed.groupby(["from", "to"]).size().reset_index(name="count_1")
    )
    file2_counts = (
        file2_renamed.groupby(["from", "to"]).size().reset_index(name="count_2")
    )

    # Merge the counts and compare
    merged_counts = pd.merge(
        file1_counts, file2_counts, on=["from", "to"], how="outer"
    ).fillna(0)

    # Find differences
    differences = merged_counts[merged_counts["count_1"] != merged_counts["count_2"]]

    # Print results
    print("\nFrom-To pairs with different counts:")
    print(differences.sort_values("count_1", ascending=False))
    print(f"\nTotal different pairs: {len(differences)}")
    print(f"Total sum of count_2 differences: {differences['count_2'].sum()}")
    print(f"Total sum of count_1 differences: {differences['count_1'].sum()}")


def main():
    args = parse_args()
    file1_renamed, file2_renamed = count_number_of_traces(args.file1, args.file2)
    count_differences(file1_renamed, file2_renamed)


if __name__ == "__main__":
    main()
