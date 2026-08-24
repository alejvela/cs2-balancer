from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from scrapers.player_record import PlayerRecord


class CsvScraperExporter:
    """
    Exporta una colección de PlayerRecord a un archivo CSV compatible
    con el importador de jugadores.

    El exportador:

        - Mantiene un orden estable de columnas.
        - Incluye estadísticas de rendimiento.
        - Incluye actividad competitiva reciente.
        - Conserva Role, Seed y Team.
        - Conserva Source y errores de scraping.
        - Crea automáticamente el directorio de salida.
        - Puede incluir o excluir registros con errores.
        - Convierte valores None en celdas vacías.
        - Convierte booleanos en true/false.
        - Evita registros duplicados dentro de una exportación.

    La columna Team permite conservar equipos predeterminados durante
    todo el flujo:

        players.csv
            ↓
        FaceitScraper
            ↓
        PlayerRecord
            ↓
        CsvScraperExporter
            ↓
        players_stats.csv
    """

    FIELDNAMES: tuple[str, ...] = (
        # -----------------------------------------------------
        # Identidad
        # -----------------------------------------------------

        "Nick",
        "SteamID",
        "ProfileURL",
        "FaceitURL",
        "CssStatsURL",

        # -----------------------------------------------------
        # FACEIT
        # -----------------------------------------------------

        "ELO",
        "FaceitLevel",

        # -----------------------------------------------------
        # Rendimiento
        # -----------------------------------------------------

        "KD",
        "Rating",
        "ADR",
        "KPR",
        "DPR",
        "HS",
        "KAST",
        "Winrate",
        "RecentWinrate",
        "Clutch",

        "Matches",

        # -----------------------------------------------------
        # Actividad
        # -----------------------------------------------------

        "Matches0_7Days",
        "Matches8_30Days",
        "Matches31_90Days",
        "TotalMatches90Days",
        "LastMatchAt",
        "DaysSinceLastMatch",
        "ActivityHistoryComplete",

        # -----------------------------------------------------
        # Datos adicionales
        # -----------------------------------------------------

        "BannedMatchesPercentage",

        "Role",
        "Seed",
        "Team",

        # -----------------------------------------------------
        # Trazabilidad
        # -----------------------------------------------------

        "Source",
        "Error",
    )

    def __init__(
        self,
        encoding: str = "utf-8-sig",
        delimiter: str = ",",
        include_errors: bool = True,
    ) -> None:
        if not isinstance(
            encoding,
            str,
        ):
            raise TypeError(
                "encoding must be a string."
            )

        normalized_encoding = encoding.strip()

        if not normalized_encoding:
            raise ValueError(
                "encoding cannot be empty."
            )

        if not isinstance(
            delimiter,
            str,
        ):
            raise TypeError(
                "delimiter must be a string."
            )

        if len(delimiter) != 1:
            raise ValueError(
                "delimiter must contain exactly one character."
            )

        if not isinstance(
            include_errors,
            bool,
        ):
            raise TypeError(
                "include_errors must be a boolean."
            )

        self._encoding = normalized_encoding
        self._delimiter = delimiter
        self._include_errors = include_errors

    def export(
        self,
        records: Iterable[PlayerRecord],
        output: str | Path,
    ) -> Path:
        """
        Sobrescribe el CSV de salida con los registros indicados.

        Args:
            records:
                Colección de PlayerRecord.

            output:
                Ruta del archivo CSV.

        Returns:
            Ruta final del archivo generado.
        """
        record_list = self._validate_records(
            records
        )

        output_path = self._prepare_output_path(
            output
        )

        exportable_records = self._prepare_records(
            record_list
        )

        self._write_records(
            records=exportable_records,
            output_path=output_path,
            mode="w",
            write_header=True,
        )

        return output_path

    def append(
        self,
        records: Iterable[PlayerRecord],
        output: str | Path,
    ) -> Path:
        """
        Añade registros a un CSV existente.

        Si el archivo no existe o está vacío, escribe también la
        cabecera.

        Esta operación elimina duplicados dentro de la colección
        recibida, pero no compara con los registros que ya existen
        en el archivo.
        """
        record_list = self._validate_records(
            records
        )

        output_path = self._prepare_output_path(
            output
        )

        exportable_records = self._prepare_records(
            record_list
        )

        write_header = (
            not output_path.exists()
            or output_path.stat().st_size == 0
        )

        self._write_records(
            records=exportable_records,
            output_path=output_path,
            mode="a",
            write_header=write_header,
        )

        return output_path

    def export_valid(
        self,
        records: Iterable[PlayerRecord],
        output: str | Path,
    ) -> Path:
        """
        Exporta únicamente registros válidos.

        No modifica permanentemente la configuración include_errors.
        """
        record_list = self._validate_records(
            records
        )

        valid_records = [
            record
            for record in record_list
            if record.is_valid
        ]

        if not valid_records:
            raise ValueError(
                "There are no valid records to export."
            )

        output_path = self._prepare_output_path(
            output
        )

        unique_records = self._remove_duplicates(
            valid_records
        )

        self._write_records(
            records=unique_records,
            output_path=output_path,
            mode="w",
            write_header=True,
        )

        return output_path

    def export_errors(
        self,
        records: Iterable[PlayerRecord],
        output: str | Path,
    ) -> Path:
        """
        Exporta únicamente registros con errores.

        Seed y Team también se conservan para poder localizar al
        jugador dentro de la configuración original del evento.
        """
        record_list = self._validate_records(
            records
        )

        failed_records = [
            record
            for record in record_list
            if not record.is_valid
        ]

        if not failed_records:
            raise ValueError(
                "There are no failed records to export."
            )

        output_path = self._prepare_output_path(
            output
        )

        unique_records = self._remove_duplicates(
            failed_records
        )

        self._write_records(
            records=unique_records,
            output_path=output_path,
            mode="w",
            write_header=True,
        )

        return output_path

    def _prepare_records(
        self,
        records: list[PlayerRecord],
    ) -> list[PlayerRecord]:
        """
        Filtra los registros según include_errors y elimina duplicados.
        """
        filtered_records = self._filter_records(
            records
        )

        unique_records = self._remove_duplicates(
            filtered_records
        )

        if not unique_records:
            raise ValueError(
                "No records are available for export."
            )

        return unique_records

    def _write_records(
        self,
        records: list[PlayerRecord],
        output_path: Path,
        mode: str,
        write_header: bool,
    ) -> None:
        """
        Escribe los registros en el archivo.

        Args:
            records:
                Registros ya filtrados y sin duplicados.

            output_path:
                Ruta preparada del CSV.

            mode:
                'w' para sobrescribir o 'a' para añadir.

            write_header:
                Indica si debe escribirse la cabecera.
        """
        if mode not in {
            "w",
            "a",
        }:
            raise ValueError(
                "mode must be either 'w' or 'a'."
            )

        with output_path.open(
            mode,
            encoding=self._encoding,
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=self.FIELDNAMES,
                delimiter=self._delimiter,
                extrasaction="ignore",
            )

            if write_header:
                writer.writeheader()

            for record in records:
                raw_row = record.to_csv_row()

                normalized_row = self._normalize_row(
                    raw_row
                )

                writer.writerow(
                    normalized_row
                )

    def _filter_records(
        self,
        records: list[PlayerRecord],
    ) -> list[PlayerRecord]:
        """
        Aplica la configuración relacionada con registros fallidos.
        """
        if self._include_errors:
            return list(
                records
            )

        return [
            record
            for record in records
            if record.is_valid
        ]

    @staticmethod
    def _remove_duplicates(
        records: list[PlayerRecord],
    ) -> list[PlayerRecord]:
        """
        Elimina duplicados manteniendo el primer registro encontrado.

        Se utiliza PlayerRecord.identity, que prioriza SteamID y usa
        el nickname como fallback.

        La asignación Team no forma parte de la identidad. Un mismo
        jugador no puede aparecer dos veces aunque tenga Team distinto.
        """
        unique_records: list[PlayerRecord] = []
        identities: set[str] = set()

        for record in records:
            identity = record.identity

            normalized_identity = (
                str(identity)
                .strip()
                .casefold()
            )

            if normalized_identity in identities:
                continue

            identities.add(
                normalized_identity
            )

            unique_records.append(
                record
            )

        return unique_records

    @staticmethod
    def _validate_records(
        records: Iterable[PlayerRecord],
    ) -> list[PlayerRecord]:
        """
        Valida y materializa la colección de registros.
        """
        if records is None:
            raise ValueError(
                "records cannot be None."
            )

        try:
            record_list = list(
                records
            )

        except TypeError as error:
            raise TypeError(
                "records must be an iterable of PlayerRecord."
            ) from error

        if not record_list:
            raise ValueError(
                "At least one record is required."
            )

        for index, record in enumerate(
            record_list,
            start=1,
        ):
            if record is None:
                raise ValueError(
                    f"Record {index} cannot be None."
                )

            if not isinstance(
                record,
                PlayerRecord,
            ):
                raise TypeError(
                    f"Record {index} must be a "
                    "PlayerRecord instance."
                )

        return record_list

    @classmethod
    def _normalize_row(
        cls,
        row: Mapping[str, Any],
    ) -> dict[str, Any]:
        """
        Normaliza una fila antes de escribirla.

        Reglas:

            None:
                Se convierte en una celda vacía.

            bool:
                Se convierte en true o false.

            str:
                Se eliminan espacios exteriores.

            int y float:
                Se conservan.

        Solo se escriben las columnas definidas en FIELDNAMES.
        """
        if not isinstance(
            row,
            Mapping,
        ):
            raise TypeError(
                "PlayerRecord.to_csv_row() must return a mapping."
            )

        normalized: dict[str, Any] = {}

        for field_name in cls.FIELDNAMES:
            value = row.get(
                field_name
            )

            if value is None:
                normalized[
                    field_name
                ] = ""

            elif isinstance(
                value,
                bool,
            ):
                normalized[
                    field_name
                ] = (
                    "true"
                    if value
                    else "false"
                )

            elif isinstance(
                value,
                str,
            ):
                normalized[
                    field_name
                ] = value.strip()

            else:
                normalized[
                    field_name
                ] = value

        return normalized

    @staticmethod
    def _prepare_output_path(
        output: str | Path,
    ) -> Path:
        """
        Valida y prepara la ruta de salida.
        """
        if output is None:
            raise ValueError(
                "output cannot be None."
            )

        if not isinstance(
            output,
            (str, Path),
        ):
            raise TypeError(
                "output must be a string or Path."
            )

        output_path = Path(
            output
        )

        if output_path.suffix.casefold() != ".csv":
            output_path = output_path.with_suffix(
                ".csv"
            )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        return output_path

    @property
    def encoding(
        self,
    ) -> str:
        return self._encoding

    @property
    def delimiter(
        self,
    ) -> str:
        return self._delimiter

    @property
    def include_errors(
        self,
    ) -> bool:
        return self._include_errors

    @property
    def fieldnames(
        self,
    ) -> tuple[str, ...]:
        """
        Devuelve el orden de columnas utilizado por el exportador.
        """
        return self.FIELDNAMES

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"encoding={self._encoding!r}, "
            f"delimiter={self._delimiter!r}, "
            f"include_errors={self._include_errors}, "
            f"field_count={len(self.FIELDNAMES)})"
        )
