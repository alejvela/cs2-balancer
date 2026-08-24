from __future__ import annotations

from abc import ABC, abstractmethod

from exporters.html_v2.report_context import ReportContext


class HtmlSection(ABC):
    """
    Contrato base para todas las secciones del informe HTML.

    Cada sección recibe un ReportContext ya procesado y devuelve
    únicamente su fragmento HTML.

    Las secciones no escriben archivos, no consultan el optimizador
    y no recalculan información global.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Nombre interno de la sección.
        """
        ...

    @abstractmethod
    def render(
        self,
        context: ReportContext,
    ) -> str:
        """
        Genera el fragmento HTML de la sección.
        """
        ...

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r})"
        )
