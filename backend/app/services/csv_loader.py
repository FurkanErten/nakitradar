from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import TypeVar

import pandas as pd
from pydantic import BaseModel, ValidationError

from app.domain.models import BusinessInput, Product, Order, Transaction, Receivable, Payable

T = TypeVar("T", bound=BaseModel)


class DataLoadError(ValueError):
    pass


def _read_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise DataLoadError(f"File not found: {path}")
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(path)
    raise DataLoadError(f"Unsupported file type: {suffix}")


def _clean_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.where(pd.notnull(df), None)
    return df


def _parse_rows(df: pd.DataFrame, model: type[T]) -> list[T]:
    df = _clean_frame(df)
    rows: list[T] = []
    errors: list[str] = []
    for idx, record in enumerate(df.to_dict(orient="records"), start=2):
        try:
            rows.append(model.model_validate(record))
        except ValidationError as exc:
            errors.append(f"row {idx}: {exc.errors()}")
    if errors:
        preview = " | ".join(errors[:5])
        raise DataLoadError(f"Validation failed for {model.__name__}: {preview}")
    return rows


def load_products(path: Path) -> list[Product]:
    return _parse_rows(_read_table(path), Product)


def load_orders(path: Path) -> list[Order]:
    return _parse_rows(_read_table(path), Order)


def load_transactions(path: Path) -> list[Transaction]:
    return _parse_rows(_read_table(path), Transaction)


def load_receivables(path: Path) -> list[Receivable]:
    return _parse_rows(_read_table(path), Receivable)


def load_payables(path: Path) -> list[Payable]:
    return _parse_rows(_read_table(path), Payable)


def load_business_from_folder(folder: Path, cash_balance: float = 64000, analysis_date: date | None = None) -> BusinessInput:
    analysis_date = analysis_date or date.today()
    return BusinessInput(
        analysis_date=analysis_date,
        cash_balance=cash_balance,
        products=load_products(folder / "products.csv"),
        orders=load_orders(folder / "orders.csv"),
        transactions=load_transactions(folder / "transactions.csv"),
        receivables=load_receivables(folder / "receivables.csv"),
        payables=load_payables(folder / "payables.csv"),
    )
