"""Shared proof-preservation protocol for claim extraction and verification."""

from __future__ import annotations

import re

from .structured_models import (
    CanonicalClaimIR,
    ClaimCategory,
    ClaimIRKind,
    PreservationAudit,
    PreservationLabel,
)

NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}

TENS_WORDS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

ORDINAL_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
}

TOKEN_PATTERN = r"[\w-]+(?:\s+[\w-]+)*"


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower()).strip(" ,.?!")


def _normalize_number_token(token: str) -> str | None:
    normalized = _normalize_text(token).replace(",", "")
    if re.fullmatch(r"\d+", normalized):
        return normalized
    if normalized in NUMBER_WORDS:
        return str(NUMBER_WORDS[normalized])

    parts = [part for part in re.split(r"[-\s]+", normalized) if part]
    if not parts:
        return None
    if len(parts) == 1 and parts[0] in ORDINAL_WORDS:
        return str(ORDINAL_WORDS[parts[0]])
    if parts[0] in TENS_WORDS:
        value = TENS_WORDS[parts[0]]
        if len(parts) == 1:
            return str(value)
        if len(parts) == 2 and parts[1] in NUMBER_WORDS and NUMBER_WORDS[parts[1]] < 10:
            return str(value + NUMBER_WORDS[parts[1]])
    return None


def _normalize_symbol_token(token: str) -> str | None:
    normalized = _normalize_text(token).strip(",")
    number = _normalize_number_token(normalized)
    if number is not None:
        return number
    if re.fullmatch(r"[a-zA-Z_]\w*", normalized):
        return normalized
    return None


def _canonicalize_predicate(text: str) -> str | None:
    normalized = _normalize_text(text)

    self_eq = re.fullmatch(r"([a-zA-Z_]\w*)\s+is\s+equal\s+to\s+itself", normalized)
    if self_eq:
        variable = self_eq.group(1)
        return f"{variable} = {variable}"

    direct = re.fullmatch(
        r"([a-zA-Z_]\w*|\d+)\s*(<=|>=|<|>|=)\s*([a-zA-Z_]\w*|\d+)",
        normalized,
    )
    if direct:
        return (
            f"{direct.group(1)} {direct.group(2)} {direct.group(3)}"
        )

    patterns = [
        (
            rf"({TOKEN_PATTERN})\s+is\s+no\s+greater\s+than\s+({TOKEN_PATTERN})",
            "<=",
        ),
        (
            rf"({TOKEN_PATTERN})\s+is\s+no\s+less\s+than\s+({TOKEN_PATTERN})",
            ">=",
        ),
        (
            rf"({TOKEN_PATTERN})\s+is\s+greater\s+than\s+or\s+equal\s+to\s+({TOKEN_PATTERN})",
            ">=",
        ),
        (
            rf"({TOKEN_PATTERN})\s+is\s+less\s+than\s+or\s+equal\s+to\s+({TOKEN_PATTERN})",
            "<=",
        ),
        (rf"({TOKEN_PATTERN})\s+is\s+strictly\s+larger\s+than\s+({TOKEN_PATTERN})", ">"),
        (rf"({TOKEN_PATTERN})\s+is\s+strictly\s+less\s+than\s+({TOKEN_PATTERN})", "<"),
        (rf"({TOKEN_PATTERN})\s+is\s+greater\s+than\s+({TOKEN_PATTERN})", ">"),
        (rf"({TOKEN_PATTERN})\s+is\s+less\s+than\s+({TOKEN_PATTERN})", "<"),
        (rf"({TOKEN_PATTERN})\s+exceeds\s+({TOKEN_PATTERN})", ">"),
        (rf"({TOKEN_PATTERN})\s+equals\s+({TOKEN_PATTERN})", "="),
        (rf"({TOKEN_PATTERN})\s+is\s+equal\s+to\s+({TOKEN_PATTERN})", "="),
    ]

    for pattern, operator in patterns:
        match = re.fullmatch(pattern, normalized)
        if not match:
            continue
        left = _normalize_symbol_token(match.group(1))
        right = _normalize_symbol_token(match.group(2))
        if left and right:
            return f"{left} {operator} {right}"

    return None


def canonicalize_surface_claim(text: str) -> tuple[str | None, ClaimCategory | None]:
    """Recover a canonical claim from a surface form using deterministic rules."""
    normalized = _normalize_text(text)
    normalized = re.sub(
        r"^(please\s+formalize(?:\s+the\s+statement)?\s+that\s+)",
        "",
        normalized,
    )

    direct_patterns = [
        (r"^\d+\s*\+\s*\d+\s*=\s*\d+$", ClaimCategory.ARITHMETIC),
        (r"^\d+\s*\*\s*\d+\s*=\s*\d+$", ClaimCategory.MULTIPLICATION),
        (r"^\d+\s*-\s*\d+\s*=\s*\d+$", ClaimCategory.SUBTRACTION),
        (r"^factorial\b.+?=\s*\d+$", ClaimCategory.FACTORIAL),
        (r"^fibonacci\b.+?=\s*\d+$", ClaimCategory.FIBONACCI),
        (r"^gcd\b.+?=\s*\d+$", ClaimCategory.GCD),
        (r"^\d+\s*(<=|>=|<|>)\s*\d+$", ClaimCategory.INEQUALITY),
    ]
    for pattern, category in direct_patterns:
        if re.fullmatch(pattern, normalized):
            inferred = category
            if inferred is None:
                predicate = _canonicalize_predicate(normalized)
                if predicate is not None:
                    return predicate, ClaimCategory.INEQUALITY
            return normalized, inferred

    arithmetic_patterns = [
        (
            rf"({TOKEN_PATTERN})\s+plus\s+({TOKEN_PATTERN})\s+(?:equals|is)\s+({TOKEN_PATTERN})",
            "+",
            ClaimCategory.ARITHMETIC,
            False,
        ),
        (
            rf"({TOKEN_PATTERN})\s+(?:times|multiplied by)\s+({TOKEN_PATTERN})\s+(?:equals|is)\s+({TOKEN_PATTERN})",
            "*",
            ClaimCategory.MULTIPLICATION,
            False,
        ),
        (
            rf"({TOKEN_PATTERN})\s+minus\s+({TOKEN_PATTERN})\s+(?:equals|is)\s+({TOKEN_PATTERN})",
            "-",
            ClaimCategory.SUBTRACTION,
            False,
        ),
        (
            rf"adding\s+({TOKEN_PATTERN})\s+and\s+({TOKEN_PATTERN})\s+yields\s+({TOKEN_PATTERN})",
            "+",
            ClaimCategory.ARITHMETIC,
            False,
        ),
        (
            rf"the\s+product\s+of\s+({TOKEN_PATTERN})\s+and\s+({TOKEN_PATTERN})\s+is\s+({TOKEN_PATTERN})",
            "*",
            ClaimCategory.MULTIPLICATION,
            False,
        ),
        (
            rf"subtracting\s+({TOKEN_PATTERN})\s+from\s+({TOKEN_PATTERN})\s+gives\s+({TOKEN_PATTERN})",
            "-",
            ClaimCategory.SUBTRACTION,
            True,
        ),
    ]
    for pattern, operator, category, reverse_operands in arithmetic_patterns:
        match = re.fullmatch(pattern, normalized)
        if not match:
            continue
        if reverse_operands:
            left = _normalize_symbol_token(match.group(2))
            right = _normalize_symbol_token(match.group(1))
            result = _normalize_symbol_token(match.group(3))
        else:
            left = _normalize_symbol_token(match.group(1))
            right = _normalize_symbol_token(match.group(2))
            result = _normalize_symbol_token(match.group(3))
        if left and right and result:
            return f"{left} {operator} {right} = {result}", category

    factorial_match = re.fullmatch(
        rf"(?:the\s+)?({TOKEN_PATTERN})\s+factorial\s+(?:equals|is)\s+({TOKEN_PATTERN})",
        normalized,
    )
    if factorial_match:
        left = _normalize_symbol_token(factorial_match.group(1))
        right = _normalize_symbol_token(factorial_match.group(2))
        if left and right:
            return f"factorial {left} = {right}", ClaimCategory.FACTORIAL

    fibonacci_match = re.fullmatch(
        rf"the\s+({TOKEN_PATTERN})\s+fibonacci\s+number\s+is\s+({TOKEN_PATTERN})",
        normalized,
    )
    if fibonacci_match:
        n = _normalize_symbol_token(fibonacci_match.group(1))
        result = _normalize_symbol_token(fibonacci_match.group(2))
        if n and result:
            return f"fibonacci {n} = {result}", ClaimCategory.FIBONACCI

    gcd_match = re.fullmatch(
        rf"the\s+greatest\s+common\s+divisor\s+of\s+({TOKEN_PATTERN})\s+and\s+({TOKEN_PATTERN})\s+is\s+({TOKEN_PATTERN})",
        normalized,
    )
    if gcd_match:
        a = _normalize_symbol_token(gcd_match.group(1))
        b = _normalize_symbol_token(gcd_match.group(2))
        result = _normalize_symbol_token(gcd_match.group(3))
        if a and b and result:
            return f"gcd({a}, {b}) = {result}", ClaimCategory.GCD

    predicate = _canonicalize_predicate(normalized)
    if predicate is not None:
        return predicate, ClaimCategory.INEQUALITY

    implication_match = re.fullmatch(r"if\s+(.+?),?\s+then\s+(.+)", normalized)
    if implication_match:
        hypothesis = _canonicalize_predicate(implication_match.group(1))
        conclusion = _canonicalize_predicate(implication_match.group(2))
        if hypothesis and conclusion:
            return (
                f"if {hypothesis} then {conclusion}",
                ClaimCategory.LOGIC_IMPLICATION,
            )

    forall_direct = re.fullmatch(r"forall\s+([a-zA-Z_]\w*),\s+(.+)", normalized)
    if forall_direct:
        variable = forall_direct.group(1)
        property_text = _canonicalize_predicate(forall_direct.group(2))
        if property_text:
            return f"forall {variable}, {property_text}", ClaimCategory.LOGIC_FORALL

    exists_direct = re.fullmatch(
        r"exists\s+([a-zA-Z_]\w*)\s+such\s+that\s+(.+)",
        normalized,
    )
    if exists_direct:
        variable = exists_direct.group(1)
        property_text = _canonicalize_predicate(exists_direct.group(2))
        if property_text:
            return (
                f"exists {variable} such that {property_text}",
                ClaimCategory.LOGIC_EXISTS,
            )

    exists_match = re.fullmatch(r"there\s+is\s+an?\s+([a-zA-Z_]\w*)\s+(.+)", normalized)
    if exists_match:
        variable = exists_match.group(1)
        property_text = _canonicalize_predicate(f"{variable} {exists_match.group(2)}")
        if property_text is None:
            property_text = _canonicalize_predicate(
                f"{variable} is {exists_match.group(2)}"
            )
        if property_text:
            return (
                f"exists {variable} such that {property_text}",
                ClaimCategory.LOGIC_EXISTS,
            )

    forall_match = re.fullmatch(r"(?:any|every)\s+([a-zA-Z_]\w*)\s+(.+)", normalized)
    if forall_match:
        variable = forall_match.group(1)
        property_text = _canonicalize_predicate(f"{variable} {forall_match.group(2)}")
        if property_text:
            return f"forall {variable}, {property_text}", ClaimCategory.LOGIC_FORALL

    return None, None


def build_claim_ir(
    canonical_text: str,
    category: ClaimCategory | str | None = None,
    *,
    parser: str = "deterministic",
) -> CanonicalClaimIR | None:
    """Build a persistent IR for a supported canonical claim."""
    normalized = _normalize_text(canonical_text)

    patterns = [
        (
            ClaimIRKind.ARITHMETIC,
            re.fullmatch(r"(\d+)\s*\+\s*(\d+)\s*=\s*(\d+)", normalized),
            "+",
            ("left", "right", "result"),
        ),
        (
            ClaimIRKind.MULTIPLICATION,
            re.fullmatch(r"(\d+)\s*\*\s*(\d+)\s*=\s*(\d+)", normalized),
            "*",
            ("left", "right", "result"),
        ),
        (
            ClaimIRKind.SUBTRACTION,
            re.fullmatch(r"(\d+)\s*-\s*(\d+)\s*=\s*(\d+)", normalized),
            "-",
            ("left", "right", "result"),
        ),
        (
            ClaimIRKind.FACTORIAL,
            re.fullmatch(r"factorial\s*\(?\s*(\d+)\s*\)?\s*=\s*(\d+)", normalized),
            "=",
            ("input", "output"),
        ),
        (
            ClaimIRKind.FIBONACCI,
            re.fullmatch(r"fibonacci\s*\(?\s*(\d+)\s*\)?\s*=\s*(\d+)", normalized),
            "=",
            ("n", "result"),
        ),
        (
            ClaimIRKind.GCD,
            re.fullmatch(r"gcd\s*\(?\s*(\d+)\s*,\s*(\d+)\s*\)?\s*=\s*(\d+)", normalized),
            "=",
            ("a", "b", "result"),
        ),
        (
            ClaimIRKind.INEQUALITY,
            re.fullmatch(r"([a-zA-Z_]\w*|\d+)\s*(<=|>=|<|>)\s*([a-zA-Z_]\w*|\d+)", normalized),
            None,
            ("left", "op", "right"),
        ),
    ]
    for kind, match, operator, field_names in patterns:
        if not match:
            continue
        operands = list(match.groups())
        bindings = {
            field_name: operand
            for field_name, operand in zip(field_names, operands, strict=True)
        }
        resolved_operator = operator or bindings.get("op")
        return CanonicalClaimIR(
            kind=kind,
            canonical_text=normalized,
            operator=resolved_operator,
            operands=operands,
            bindings=bindings,
            parser=parser,
        )

    implication_match = re.fullmatch(r"if\s+(.+)\s+then\s+(.+)", normalized)
    if implication_match:
        hypothesis = implication_match.group(1).strip()
        conclusion = implication_match.group(2).strip()
        return CanonicalClaimIR(
            kind=ClaimIRKind.LOGIC_IMPLICATION,
            canonical_text=normalized,
            operator="->",
            operands=[hypothesis, conclusion],
            bindings={"hypothesis": hypothesis, "conclusion": conclusion},
            parser=parser,
        )

    forall_match = re.fullmatch(r"forall\s+([a-zA-Z_]\w*),\s+(.+)", normalized)
    if forall_match:
        variable = forall_match.group(1)
        property_text = forall_match.group(2).strip()
        return CanonicalClaimIR(
            kind=ClaimIRKind.LOGIC_FORALL,
            canonical_text=normalized,
            operator="forall",
            operands=[variable, property_text],
            bindings={"variable": variable, "property": property_text},
            parser=parser,
        )

    exists_match = re.fullmatch(
        r"exists\s+([a-zA-Z_]\w*)\s+such\s+that\s+(.+)",
        normalized,
    )
    if exists_match:
        variable = exists_match.group(1)
        property_text = exists_match.group(2).strip()
        return CanonicalClaimIR(
            kind=ClaimIRKind.LOGIC_EXISTS,
            canonical_text=normalized,
            operator="exists",
            operands=[variable, property_text],
            bindings={"variable": variable, "property": property_text},
            parser=parser,
        )

    if category is not None:
        category_value = category.value if isinstance(category, ClaimCategory) else str(category)
        return CanonicalClaimIR(
            kind=ClaimIRKind.UNKNOWN,
            canonical_text=normalized,
            operands=[normalized],
            bindings={"category": category_value},
            parser=parser,
        )

    return None


class PreservationAuditor:
    """Conservative surface-to-canonical preservation checker."""

    def audit(
        self,
        *,
        surface_text: str,
        canonical_text: str,
        category: ClaimCategory | str | None = None,
    ) -> PreservationAudit:
        surface_canonical_text, _ = canonicalize_surface_claim(surface_text)
        canonical_ir = build_claim_ir(canonical_text, category, parser="canonical")

        if canonical_ir is None:
            return PreservationAudit(
                label=PreservationLabel.UNKNOWN,
                passed=False,
                surface_text=surface_text,
                canonical_text=canonical_text,
                surface_canonical_text=surface_canonical_text,
                rationale="Canonical claim could not be parsed into a supported IR.",
            )

        if surface_canonical_text is None:
            return PreservationAudit(
                label=PreservationLabel.UNKNOWN,
                passed=False,
                surface_text=surface_text,
                canonical_text=canonical_text,
                surface_canonical_text=None,
                rationale=(
                    "Could not deterministically recover a canonical claim from "
                    "the surface text."
                ),
            )

        if _normalize_text(surface_canonical_text) == _normalize_text(canonical_text):
            label = (
                PreservationLabel.EXACT
                if _normalize_text(surface_text) == _normalize_text(canonical_text)
                else PreservationLabel.EQUIVALENT
            )
            return PreservationAudit(
                label=label,
                passed=True,
                surface_text=surface_text,
                canonical_text=canonical_text,
                surface_canonical_text=surface_canonical_text,
                rationale="Deterministic canonicalization matched the proof target.",
            )

        return PreservationAudit(
            label=PreservationLabel.DRIFT,
            passed=False,
            surface_text=surface_text,
            canonical_text=canonical_text,
            surface_canonical_text=surface_canonical_text,
            rationale=(
                "Deterministic canonicalization recovered a different claim from "
                "the surface text, so proving the selected target would risk "
                "silent correction."
            ),
        )
