"""Tests for the auto-detect rules inference module."""
from __future__ import annotations

import pandas as pd

from src.infer import infer_config


def test_email_column_detected():
    df = pd.DataFrame({"contact": ["a@example.com", "b@test.org", "c@foo.net"]})
    config, explanations = infer_config(df)
    assert "contact" in config["range_and_format"].get("email_columns", [])
    assert "email" in explanations["contact"]


def test_date_column_ymd_detected():
    df = pd.DataFrame({"created": ["2024-01-15", "2024-06-20", "2023-12-01"]})
    config, explanations = infer_config(df)
    assert "created" in config["range_and_format"].get("date_columns", [])
    assert "date" in explanations["created"]


def test_date_column_dmy_detected():
    df = pd.DataFrame({"joined": ["15-01-2024", "20-06-2024", "01-12-2023"]})
    config, _explanations = infer_config(df)
    assert "joined" in config["range_and_format"].get("date_columns", [])


def test_date_column_dmy_slash_detected():
    df = pd.DataFrame({"dob": ["15/01/2024", "20/06/2024", "01/12/2023"]})
    config, _explanations = infer_config(df)
    assert "dob" in config["range_and_format"].get("date_columns", [])


def test_percentage_column_detected():
    df = pd.DataFrame({"score": [85, 90, 72, 100, 45]})
    config, explanations = infer_config(df)
    assert "score" in config["range_and_format"].get("percentage_columns", [])
    assert "percentage" in explanations["score"]


def test_id_column_detected():
    df = pd.DataFrame({"order_id": [1, 2, 3, 4, 5]})
    config, explanations = infer_config(df)
    assert "order_id" in config["duplicates"]["subset"]
    assert "id-like" in explanations["order_id"]


def test_plain_text_no_format_rule():
    df = pd.DataFrame({"city": ["Mumbai", "Delhi", "Chennai", "Kolkata"]})
    config, explanations = infer_config(df)
    rf = config["range_and_format"]
    assert "city" not in rf.get("email_columns", [])
    assert "city" not in rf.get("date_columns", [])
    assert "city" not in rf.get("percentage_columns", [])
    assert "no specific format" in explanations.get("city", "")


def test_empty_dataframe():
    df = pd.DataFrame()
    config, explanations = infer_config(df)
    assert config["required_columns"]["columns"] == []
    assert explanations == {}


def test_all_columns_required():
    df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
    config, _ = infer_config(df)
    assert set(config["required_columns"]["columns"]) == {"a", "b", "c"}


def test_missing_values_columns_low_nulls():
    df = pd.DataFrame({"name": ["Alice", "Bob", "Charlie", "Dana", "Eve"]})
    config, _ = infer_config(df)
    assert "name" in config["missing_values"]["columns"]


def test_end_to_end_orders_csv(tmp_path):
    csv_path = tmp_path / "orders.csv"
    csv_path.write_text(
        "order_id,customer_email,order_date,discount_pct,city\n"
        "1001,alice@shop.com,2024-03-15,10,Mumbai\n"
        "1002,bob@shop.com,2024-03-16,15,Delhi\n"
        "1003,charlie@shop.com,2024-03-17,5,Chennai\n"
        "1004,dana@shop.com,2024-03-18,20,Kolkata\n"
        "1005,eve@shop.com,2024-03-19,0,Pune\n"
    )
    df = pd.read_csv(csv_path)
    config, explanations = infer_config(df)

    assert "customer_email" in config["range_and_format"].get("email_columns", [])
    assert "order_date" in config["range_and_format"].get("date_columns", [])
    assert "discount_pct" in config["range_and_format"].get("percentage_columns", [])
    assert "order_id" in config["duplicates"]["subset"]
    assert "no specific format" in explanations.get("city", "")
