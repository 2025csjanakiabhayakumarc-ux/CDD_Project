
import pandas as pd

from src.duplicates import find_duplicates


def test_no_duplicates():
    df = pd.read_csv("sample_data/good.csv")

    result = find_duplicates(df)

    assert len(result) == 0


def test_detect_duplicates():
    df = pd.read_csv("sample_data/bad.csv")

    result = find_duplicates(df)

    assert len(result) == 2


def test_duplicates_using_selected_columns():
    df = pd.DataFrame({
        "name": ["Anu", "Anu", "Ravi"],
        "age": [20, 20, 21],
        "city": ["Delhi", "Mumbai", "Pune"]
    })

    result = find_duplicates(df, subset=["name", "age"])

    assert len(result) == 1


def test_empty_dataframe():
    df = pd.DataFrame(columns=["name", "age"])

    result = find_duplicates(df)

    assert len(result) == 0
