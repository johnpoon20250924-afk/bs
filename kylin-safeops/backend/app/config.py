import os
from dataclasses import dataclass
from functools import lru_cache


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    safeops_mode: str
    safeops_mode_raw: str
    safeops_mode_valid: bool
    deepseek_enabled: bool
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    runtime_auto_diagnose: bool
    runtime_auto_diagnose_min_confidence: float


@lru_cache
def get_settings() -> Settings:
    raw_mode = os.getenv("SAFEOPS_MODE", "auto").strip().lower()
    mode_valid = raw_mode in {"demo", "real", "auto"}
    mode = raw_mode
    if not mode_valid:
        mode = "demo"

    return Settings(
        safeops_mode=mode,
        safeops_mode_raw=raw_mode,
        safeops_mode_valid=mode_valid,
        deepseek_enabled=os.getenv("DEEPSEEK_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"},
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner"),
        runtime_auto_diagnose=os.getenv("SAFEOPS_RUNTIME_AUTO_DIAGNOSE", "false").strip().lower() in {"1", "true", "yes", "on"},
        runtime_auto_diagnose_min_confidence=_float_env("SAFEOPS_RUNTIME_AUTO_DIAGNOSE_MIN_CONFIDENCE", 0.9),
    )
