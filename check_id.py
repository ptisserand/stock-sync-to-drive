#!/usr/bin/env python

import sys
import pandas as pd

def count_same_id(first, second) -> (int, int):
    name_key = 'name'
    id_key = 'id'
    ok = 0
    nok = 0

    # retrieve common names
    first_names = first['name'].dropna()
    second_names = second['name'].dropna()
    common_names = list(set(first_names).intersection(set(second_names)))

    for nn in common_names:
        first_idx = first_names[first_names == nn].index.values
        second_idx = second_names[second_names == nn].index.values
        first_id = first['id'][first_idx].iloc[0]
        second_id = second['id'][second_idx].iloc[0]

        if first_id != f"__export__.product_template_{second_id}":
            print(f"{first['id'][first_idx]} != {second['id'][second_idx]}")
            nok = nok + 1
        else:
            ok = ok + 1
    
    return ok, nok

if __name__ == "__main__":
    first_file = sys.argv[1]
    second_file = sys.argv[2]

    first = pd.read_excel(first_file)
    second = pd.read_excel(second_file)
    ok, nok = count_same_id(first, second)
    print("########")
    print(f"OK: {ok} | NOK: {nok}")

