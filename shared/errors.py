from __future__ import annotations


class ContractError(RuntimeError):
    """Base error for protocol-boundary failures."""


class ValidationContractError(ContractError):
    """Raised when payload validation fails."""


class FrontendContractError(ContractError):
    """Raised when frontend tries to violate frontend boundary."""


class BackendContractError(ContractError):
    """Raised when backend fails to satisfy backend boundary."""
