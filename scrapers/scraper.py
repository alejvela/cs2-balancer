from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from scrapers.player_record import PlayerRecord


class Scraper(ABC):
    """
    Contrato base para los scrapers de estadísticas de jugadores.

    Un scraper recibe una fuente con los perfiles que deben consultarse
    y devuelve una colección de PlayerRecord.

    El scraper:

    - Obtiene datos de una fuente externa.
    - Limpia y normaliza el contenido extraído.
    - Devuelve registros independientes del modelo Player.

    El scraper no:

    - Construye equipos.
    - Calcula el Power Score.
    - Crea objetos Player.
    - Ejecuta la optimización.
    - Genera informes HTML.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Nombre legible del scraper.
        """
        ...

    @abstractmethod
    def scrape(
        self,
        source: str | Path,
    ) -> list[PlayerRecord]:
        """
        Extrae las estadísticas de todos los jugadores definidos
        en la fuente recibida.

        Args:
            source:
                Ruta al CSV o JSON que contiene los nicks,
                identificadores o URLs de los perfiles.

        Returns:
            Lista de PlayerRecord con los datos obtenidos.

        Raises:
            FileNotFoundError:
                Cuando el archivo de entrada no existe.

            ValueError:
                Cuando la fuente no contiene registros válidos.

            RuntimeError:
                Cuando se produce un error externo durante la extracción.
        """
        ...

    def scrape_many(
        self,
        sources: Sequence[str | Path],
    ) -> list[PlayerRecord]:
        """
        Ejecuta el scraper sobre varias fuentes y combina los resultados.

        Los duplicados se eliminan utilizando Steam ID cuando esté
        disponible y, en caso contrario, el nick normalizado.
        """
        if sources is None:
            raise ValueError(
                "sources cannot be None."
            )

        source_list = list(sources)

        if not source_list:
            raise ValueError(
                "At least one source is required."
            )

        records: list[PlayerRecord] = []
        identities: set[str] = set()

        for source in source_list:
            source_records = self.scrape(source)

            for record in source_records:
                identity = self._record_identity(record)

                if identity in identities:
                    continue

                identities.add(identity)
                records.append(record)

        return records

    @staticmethod
    def validate_source(
        source: str | Path,
    ) -> Path:
        """
        Valida que la fuente sea un archivo existente.
        """
        if source is None:
            raise ValueError(
                "source cannot be None."
            )

        path = Path(source)

        if not path.exists():
            raise FileNotFoundError(
                f"Source file '{path}' does not exist."
            )

        if not path.is_file():
            raise ValueError(
                f"Source '{path}' is not a file."
            )

        return path

    @staticmethod
    def _record_identity(
        record: PlayerRecord,
    ) -> str:
        """
        Obtiene una identidad estable para detectar duplicados.
        """
        if record is None:
            raise ValueError(
                "record cannot be None."
            )

        if record.steam_id:
            return (
                f"steam:"
                f"{str(record.steam_id).strip()}"
            )

        if record.nickname:
            return (
                f"nickname:"
                f"{record.nickname.strip().casefold()}"
            )

        if record.profile_url:
            return (
                f"profile:"
                f"{record.profile_url.strip().casefold()}"
            )

        return f"object:{id(record)}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(name='{self.name}')"
        )
