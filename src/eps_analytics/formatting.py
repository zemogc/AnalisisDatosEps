"""Formato de cifras en convención colombiana (punto de miles, coma decimal)."""

from __future__ import annotations


def _swap(s: str) -> str:
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def numero(valor: float, decimales: int = 0) -> str:
    return _swap(f"{valor:,.{decimales}f}")


def cop(valor: float) -> str:
    """$ 1.234.567"""
    return f"$ {numero(valor)}"


def cop_compacto(valor: float) -> str:
    """$ 1,7 MM (miles de millones), $ 85,3 M (millones) o $ 950 mil."""
    a = abs(valor)
    if a >= 1e9:
        return f"$ {numero(valor / 1e9, 2)} MM"
    if a >= 1e6:
        return f"$ {numero(valor / 1e6, 1)} M"
    if a >= 1e3:
        return f"$ {numero(valor / 1e3, 0)} mil"
    return cop(valor)


def porcentaje(valor: float, decimales: int = 1) -> str:
    return f"{numero(valor * 100, decimales)} %"
