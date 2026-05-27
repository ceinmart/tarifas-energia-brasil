"""Versao: 0.1.0
Criado em: 2026-05-27 00:00:00 -03:00
Criado por: brainstorming colaborativo
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import importlib.util
import sys
import types
from enum import StrEnum
from pathlib import Path


def _install_fake_homeassistant_modules() -> None:
    """Instala stubs minimos para importar const.py sem Home Assistant real."""
    homeassistant = sys.modules.get("homeassistant", types.ModuleType("homeassistant"))
    const = sys.modules.get("homeassistant.const", types.ModuleType("homeassistant.const"))

    class Platform(StrEnum):
        SENSOR = "sensor"

    const.Platform = Platform
    homeassistant.const = const
    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.const"] = const


def _install_fake_aiohttp_module() -> None:
    """Stub minimo de aiohttp para evitar dependencia no ambiente de teste."""
    if "aiohttp" in sys.modules:
        return
    aiohttp_stub = types.ModuleType("aiohttp")

    class ClientSession:
        pass

    class ClientError(Exception):
        pass

    aiohttp_stub.ClientSession = ClientSession
    aiohttp_stub.ClientError = ClientError
    sys.modules["aiohttp"] = aiohttp_stub


_install_fake_homeassistant_modules()
_install_fake_aiohttp_module()


_BASE_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "tarifas_energia_brasil"
_PKG_NAME = "tarifas_energia_brasil_testpkg_tributos_fallback"

if _PKG_NAME not in sys.modules:
    pkg = types.ModuleType(_PKG_NAME)
    pkg.__path__ = [str(_BASE_DIR)]  # type: ignore[attr-defined]
    sys.modules[_PKG_NAME] = pkg


def _load_package_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Carregar deps internas antes do __init__ do submodulo tributos.
_load_package_module(f"{_PKG_NAME}.const", _BASE_DIR / "const.py")
_load_package_module(f"{_PKG_NAME}.models", _BASE_DIR / "models.py")

_tributos_pkg_name = f"{_PKG_NAME}.tributos"
tributos_pkg = types.ModuleType(_tributos_pkg_name)
tributos_pkg.__path__ = [str(_BASE_DIR / "tributos")]  # type: ignore[attr-defined]
sys.modules[_tributos_pkg_name] = tributos_pkg

_load_package_module(f"{_tributos_pkg_name}.parsers", _BASE_DIR / "tributos" / "parsers.py")
tributos_mod = _load_package_module(f"{_tributos_pkg_name}", _BASE_DIR / "tributos" / "__init__.py")


def test_light_rj_fallback_registered():
    fallback = tributos_mod._TRIBUTOS_FALLBACK["LIGHT-RJ"]
    assert fallback.pis == 1.10
    assert fallback.cofins == 5.02
    assert fallback.icms == 20.00
    assert fallback.fonte.startswith("https://www.light.com.br/")
    assert fallback.confianca == "media"
    assert fallback.pendencias
