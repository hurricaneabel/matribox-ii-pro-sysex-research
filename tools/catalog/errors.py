"""Erros do catálogo multiplataforma da Matribox."""

from __future__ import annotations


class CatalogError(RuntimeError):
    """Erro base ao carregar ou validar o catálogo."""


class CatalogValidationError(CatalogError, ValueError):
    """O catálogo contém dados inválidos ou inconsistentes."""
