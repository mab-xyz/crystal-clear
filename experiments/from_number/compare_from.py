import pandas as pd
import argparse
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description="Compare two trace files")
    parser.add_argument("file1", help="First input file (should be cryo)")
    parser.add_argument("file2", help="Second input file (should be trace_number)")
    return parser.parse_args()


def clean_data(file1, file2):
    # Load the two files and replace empty strings with NaN
    file1_df = pd.read_csv(file1).replace(r"^\s*$", np.nan, regex=True)
    file2_df = pd.read_csv(file2).replace(r"^\s*$", np.nan, regex=True)

    file1_df = file1_df[file1_df["action_type"] == "create"]
    file1_df["action_to"] = file1_df["action_to"].fillna(file1_df["result_address"])
    # file2_df["trace_address"] = file2_df["trace_address"].str.replace(",", "_")

    # Rename columns for comparison
    file1_renamed = file1_df.rename(
        columns={
            # "transaction_hash": "tx_hash",
            # "trace_address": "trace_addr",
            "action_from": "from",
            # "action_to": "to",
        }
    )

    file2_renamed = file2_df.rename(
        columns={
            # "transaction_hash": "tx_hash",
            # "trace_address": "trace_addr",
            "from_address": "from",
            # "to_address": "to",
        }
    )

    print(f"Total rows in file1: {len(file1_renamed)}")
    print(f"Total rows in file2: {len(file2_renamed)}")

    return file1_renamed, file2_renamed


# compare address in file 2 but not in file 1
def compare_from_number(file1_df, file2_df):
    # Get unique 'from' addresses from both files
    file1_from = set(file1_df["from"].unique())
    file2_from = set(file2_df["from"].unique())

    print(f"\nTotal unique 'from' addresses in file1: {len(file1_from)}")
    print(f"Total unique 'from' addresses in file2: {len(file2_from)}")

    # 找出差异的地址
    different_addresses = file1_from - file2_from

    print(
        f"\nNumber of addresses in file2 not found in file1: {len(different_addresses)}"
    )
    # if different_addresses:
    # print("\nAddresses in file2 but not in file1:")
    # print(different_addresses)

    # 将集合转换为DataFrame以便保存为CSV
    different_addresses_df = pd.DataFrame(
        list(different_addresses), columns=["address"]
    )
    return different_addresses_df


if __name__ == "__main__":
    args = parse_args()
    file1_renamed, file2_renamed = clean_data(args.file1, args.file2)
    different_addresses_df = compare_from_number(file1_renamed, file2_renamed)
    if len(different_addresses_df) > 0:
        different_addresses_df.to_csv("different_addresses_1000.csv", index=False)
