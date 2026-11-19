from __future__ import annotations

import os
from pathlib import Path

from configuration.application_config import ApplicationConfig
from scrapers.csv_escraper_exporter import CsvScraperExporter
from scrapers.faceit.faceit_api_client import FaceitApiClient
from scrapers.faceit.faceit_player_record_map import FaceitPlayerRecordMapper
from scrapers.faceit.faceit_scrapper import FaceitScraper


def get_faceit_api_key() -> str:
    """
    Obtiene la API key de FACEIT desde la variable de entorno
    FACEIT_API_KEY.
    """

    api_key = os.environ.get("FACEIT_API_KEY")

    if api_key is None:
        raise RuntimeError("La variable de entorno FACEIT_API_KEY no está definida.")

    normalized = api_key.strip()

    if not normalized:
        raise RuntimeError("La variable de entorno FACEIT_API_KEY está vacía.")

    return normalized


def run_faceit_import(config: ApplicationConfig) -> Path:
    """
    Consulta FACEIT para todos los jugadores del CSV inicial.

    El CSV de entrada contiene la configuración manual:

        Nick
        FaceitNickname
        Seed
        Team

    El scraper y CsvScraperExporter deben conservar Seed y Team
    durante todo el proceso para que el CSV generado pueda utilizarse
    posteriormente tanto en modo automático como preasignado.
    """

    if not config.paths.source_players.exists():
        raise FileNotFoundError(
            f"No existe el archivo de entrada: {config.paths.source_players.resolve()}"
        )

    api_key = get_faceit_api_key()

    print()
    print("=" * 72)
    print("IMPORTACIÓN DE JUGADORES DESDE FACEIT")
    print("=" * 72)

    print(f"Entrada:              {config.paths.source_players}")

    print(f"Juego preferido:      {config.faceit.preferred_game_id}")

    print(f"Juegos fallback:      {', '.join(config.faceit.fallback_game_ids)}")

    print(f"Partidas recientes:   {config.faceit.recent_matches}")

    print()

    with FaceitApiClient(
        api_key=api_key,
        preferred_game_id=(config.faceit.preferred_game_id),
        fallback_game_ids=(config.faceit.fallback_game_ids),
        timeout=config.faceit.timeout_seconds,
        retries=config.faceit.retries,
        retry_delay=(config.faceit.retry_delay_seconds),
    ) as client:
        mapper = FaceitPlayerRecordMapper(
            game_id=config.faceit.preferred_game_id,
            source_name="FACEIT",
        )

        scraper = FaceitScraper(
            client=client,
            mapper=mapper,
            recent_matches=config.faceit.recent_matches,
            strict=config.faceit.strict,
            delay=config.faceit.delay_seconds,
            maximum_seed_one_players=(config.event.number_of_teams),
        )

        records = scraper.scrape(config.paths.source_players)

        scraper_errors = scraper.errors

    valid_records = [record for record in records if record.is_valid]

    failed_records = [record for record in records if not record.is_valid]

    print(f"Jugadores esperados:  {config.event.expected_player_count}")

    print(f"Jugadores válidos:    {len(valid_records)}")

    print(f"Jugadores con error:  {len(failed_records)}")

    if failed_records:
        print()
        print("JUGADORES CON ERROR")
        print("-" * 72)

        for record in failed_records:
            print(f"- {record.nickname}: {record.error or 'Error desconocido'}")

        CsvScraperExporter(
            include_errors=True,
        ).export(
            records=failed_records,
            output=config.paths.faceit_errors,
        )

        print()

        print(f"Errores guardados en: {config.paths.faceit_errors.resolve()}")

    if scraper_errors:
        print()
        print("DETALLE TÉCNICO")
        print("-" * 72)

        for error in scraper_errors:
            print(
                f"Fila {error.get('row')}: "
                f"{error.get('nick')} / "
                f"{error.get('faceit_nickname')} -> "
                f"{error.get('error')}"
            )

    if len(valid_records) != config.event.expected_player_count:
        raise RuntimeError(
            "El número de jugadores válidos no coincide "
            "con el esperado. "
            f"Esperados: {config.event.expected_player_count}. "
            f"Obtenidos: {len(valid_records)}."
        )

    generated_file = CsvScraperExporter(
        include_errors=False,
    ).export(
        records=valid_records,
        output=config.paths.generated_stats,
    )

    print()

    print(f"CSV de estadísticas generado: {generated_file.resolve()}")

    return generated_file


def resolve_players_file(config: ApplicationConfig) -> Path:
    """
    Devuelve el CSV que debe utilizar la aplicación.

    Cuando config.faceit.run_import=True se regeneran primero las
    estadísticas.

    Cuando es False se reutiliza players_stats.csv.
    """

    if config.faceit.run_import:
        return run_faceit_import(config)

    if not config.paths.generated_stats.exists():
        raise FileNotFoundError(
            f"No existe el archivo generado: {config.paths.generated_stats.resolve()}"
        )

    return config.paths.generated_stats
