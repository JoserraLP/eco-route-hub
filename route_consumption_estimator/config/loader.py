import os
import re
import yaml
from pathlib import Path
from typing import Any

from route_consumption_estimator import CONFIG_FILE_DIR
from route_consumption_estimator.config.models import AppConfig

ENV_PATTERN = re.compile(r"\$\{([^}^{]+)\}")


def _replace_env_vars(obj: Any) -> Any:
    """
    Recursively replace ${VAR_NAME} with environment variable value.
    """

    if isinstance(obj, dict):
        return {k: _replace_env_vars(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_replace_env_vars(i) for i in obj]

    if isinstance(obj, str):
        match = ENV_PATTERN.fullmatch(obj)
        if match:
            env_var = match.group(1)
            value = os.getenv(env_var)

            if value is None:
                raise RuntimeError(
                    f"Environment variable '{env_var}' is not set"
                )

            return value

        return obj

    return obj


def load_config(path: str = CONFIG_FILE_DIR) -> AppConfig:

    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(config_path, "r") as f:
        raw_yaml = yaml.safe_load(f) or {}

    processed_yaml = _replace_env_vars(raw_yaml)

    return AppConfig(**processed_yaml)
