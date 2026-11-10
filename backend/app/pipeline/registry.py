"""Check registry (@check decorator)."""

from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

VALID_STAGES = {f"S{i}" for i in range(14)}

_registry: dict[str, "CheckSpec"] = {}


@dataclass(frozen=True)
class CheckSpec:
    id: str
    stage: str
    version: int
    mandatory: bool
    reads: tuple[str, ...]
    adapters: tuple[str, ...]
    timeout_s: float
    fn: Callable[..., Awaitable[list[Any]]]


def check(
    *,
    id: str,
    stage: str,
    version: int,
    mandatory: bool = True,
    reads: tuple[str, ...] = (),
    adapters: tuple[str, ...] = (),
    timeout_s: float = 1.0,
) -> Callable[[Callable[..., Awaitable[list[Any]]]], Callable[..., Awaitable[list[Any]]]]:
    def deco(fn: Callable[..., Awaitable[list[Any]]]) -> Callable[..., Awaitable[list[Any]]]:
        if id in _registry:
            raise ValueError(f"duplicate check id: {id}")
        if stage not in VALID_STAGES:
            raise ValueError(f"invalid stage: {stage}")
        _registry[id] = CheckSpec(
            id=id,
            stage=stage,
            version=version,
            mandatory=mandatory,
            reads=tuple(reads),
            adapters=tuple(adapters),
            timeout_s=timeout_s,
            fn=fn,
        )
        return fn

    return deco


def get(spec_id: str) -> CheckSpec:
    return _registry[spec_id]


def all_specs() -> list[CheckSpec]:
    return list(_registry.values())


def specs_by_stage(stage: str) -> list[CheckSpec]:
    return [s for s in _registry.values() if s.stage == stage]


def clear() -> None:
    _registry.clear()
