"""Errors for transactions whose original state cannot be guaranteed."""


class TransactionIntegrityError(RuntimeError):
    """Restoration takes precedence; all earlier failures remain inspectable.

    The restoration/validation failure is always the direct ``__cause__``.
    Explicit references avoid losing simultaneous operation and undo failures
    (and avoid constructing cycles in Python's implicit context chain).
    """

    def __init__(
        self,
        message: str,
        *,
        operation_error: Exception | None = None,
        undo_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.operation_error = operation_error
        self.undo_error = undo_error
        for name, error in (("operation", operation_error), ("undo", undo_error)):
            if error is not None:
                self.add_note(f"Earlier {name} failure: {error!r}")
