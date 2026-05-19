"""
google_sheets_dataset.py
Dataset personalizado de Kedro para cargar archivos Excel publicados
desde Google Sheets vía URL pública (pub?output=xlsx).

Motivo: kedro_datasets.pandas.ExcelDataset usa fsspec internamente,
lo que genera requests malformadas hacia Google Sheets → HTTP 400.
Este dataset evita fsspec y usa requests directamente, replicando
el comportamiento de pd.read_excel(url) en un notebook.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd
import requests
from kedro.io import AbstractDataset


class GoogleSheetsDataset(AbstractDataset):
    """
    Carga una hoja de Google Sheets publicada como Excel (.xlsx)
    directamente desde su URL pública.

    Uso en catalog.yml:
        my_dataset:
          type: <package>.datasets.google_sheets_dataset.GoogleSheetsDataset
          url: "https://docs.google.com/spreadsheets/d/e/.../pub?output=xlsx"
          load_args:
            sheet_name: 0
    """

    def __init__(
        self,
        url: str,
        load_args: dict[str, Any] | None = None,
    ) -> None:
        """
        Args:
            url       : URL pública de Google Sheets con output=xlsx.
            load_args : Argumentos adicionales para pd.read_excel()
                        (ej: sheet_name, header, dtype, usecols).
        """
        self._url = url
        # Si no se pasan load_args, inicializar como dict vacío para evitar None
        self._load_args = load_args or {}

    def _load(self) -> pd.DataFrame:
        """
        Descarga el archivo Excel desde la URL y lo carga como DataFrame.
        Usa requests para controlar headers y seguimiento de redirects,
        evitando el comportamiento problemático de fsspec con Google Sheets.
        """
        # Headers que simulan un navegador real.
        # Google Sheets puede rechazar requests sin User-Agent (→ 400 o 403).
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; KedroDataset/1.0)"
            )
        }

        response = requests.get(
            self._url,
            headers=headers,
            timeout=30,       # Timeout explícito para evitar cuelgues en producción
            allow_redirects=True,  # Google Sheets redirige antes de servir el archivo
        )

        # Lanzar excepción descriptiva si la respuesta no es 200
        response.raise_for_status()

        # Cargar el contenido binario de la respuesta directamente en pandas
        # sin necesidad de escribir un archivo temporal en disco
        return pd.read_excel(BytesIO(response.content), **self._load_args)

    def _save(self, data: pd.DataFrame) -> None:
        """
        Escritura no soportada: una URL pública de Google Sheets es de solo lectura.
        """
        raise NotImplementedError(
            "GoogleSheetsDataset es de solo lectura. "
            "No es posible escribir sobre una URL pública de Google Sheets."
        )

    def _describe(self) -> dict[str, Any]:
        """
        Descripción del dataset para logs y el catálogo de Kedro.
        """
        return {
            "url": self._url,
            "load_args": self._load_args,
        }