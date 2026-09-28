"""
Configuration loader module.

Provides functionality to load YAML configuration files, recursively resolve and substitute 
environment variables (with support for inline variables and optional default values), 
and instantiate structured configuration models.
"""

import os
import re
from pathlib import Path
from typing import Any, Union
import yaml

from eco_route_hub.config.models import AppConfig

# Pattern matching ${VAR_NAME} or ${VAR_NAME:-default_value}
ENV_PATTERN = re.compile(r"\$\{([^}^{]+)\}")


def _replace_env_vars(obj: Any) -> Any:
    """
    Recursively traverse data structures and replace ${VAR_NAME} placeholders 
    with corresponding environment variable values.

    Supports optional default values using syntax: ${VAR_NAME:-default_value}.

    Args:
        obj (Any): Data structure (dict, list, str, or primitive) to process.

    Returns:
        Any: Processed data structure with environment variables resolved.

    Raises:
        KeyError: If an environment variable is referenced without a default and is not set.
    """
    if isinstance(obj, dict):
        return {k: _replace_env_vars(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_replace_env_vars(i) for i in obj]

    if isinstance(obj, str):
        def _replacer(match: re.Match) -> str:
            expr = match.group(1)
            # Support optional default value syntax: ${VAR_NAME:-default}
            if ":-" in expr:
                env_var, default_val = expr.split(":-", 1)
            else:
                env_var, default_val = expr, None

            value = os.getenv(env_var)
            if value is not None:
                return value
            if default_val is not None:
                return default_val

            raise KeyError(
                f"Configuration error: Environment variable '{env_var}' is not set "
                f"and no default value was provided."
            )

        # Allows both full string replacement and inline string interpolation (e.g. "sqlite:///${DB_PATH}")
        return ENV_PATTERN.sub(_replacer, obj)

    return obj


def load_config(path: Union[str, Path]) -> AppConfig:
    """
    Load YAML configuration file and return a validated AppConfig instance.

    Args:
        path (Union[str, Path]): Path to the YAML configuration file. 
            Defaults to CONFIG_FILE_DIR.

    Returns:
        AppConfig: Validated application configuration model instance.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        yaml.YAMLError: If the YAML file contains syntax errors.
        KeyError: If a required environment variable is missing.
        ValueError: If the configuration structure fails validation.
    """
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path.resolve()}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw_yaml = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Failed to parse YAML configuration file '{config_path}': {exc}") from exc

    # Recursively resolve environment variable place-holders
    processed_yaml = _replace_env_vars(raw_yaml)

    try:
        return AppConfig(**processed_yaml)
    except Exception as exc:
        raise ValueError(f"Failed to validate AppConfig from '{config_path}': {exc}") from exc
