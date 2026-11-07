"""VALIDATION capability: structural invariant reports for every structure."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..core.metadata import describe
from ..core.results import DSAExecutionContext, ValidationReport
from ..validation.validators import VALIDATORS, validator_for
from .base import BaseDSACapability, operation


class ValidationService(BaseDSACapability):
    capability = "VALIDATION"

    @operation(describe("VALIDATE", capability, set(VALIDATORS), "O(n) / O(V+E)", "O(n)"))
    def _validate(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> ValidationReport:
        validator = validator_for(context.structure_type, args.get("key"))
        report: ValidationReport = validator.validate(
            context.state, raise_on_error=bool(args.get("raise_on_error", False))
        )
        if not report.valid:
            context.warn("INVARIANT_VIOLATIONS", f"{len(report.violations)} violation(s)")
        return report
