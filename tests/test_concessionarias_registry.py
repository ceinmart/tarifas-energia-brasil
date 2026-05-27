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


_install_fake_homeassistant_modules()


def _load_const_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "tarifas_energia_brasil"
        / "const.py"
    )
    spec = importlib.util.spec_from_file_location(
        "tarifas_energia_brasil_testpkg_const.const", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


const_mod = _load_const_module()


def test_light_rj_listed_as_supported():
    nomes = const_mod.obter_concessionarias_suportadas_para_fluxo()
    assert "LIGHT-RJ" in nomes


def test_light_rj_registry_metadata():
    info = const_mod.CONCESSIONARIAS_SUPORTADAS["LIGHT-RJ"]
    assert info.slug == "light_rj"
    assert info.nome == "LIGHT-RJ"
    assert info.suportada is True
    assert info.extrator_tributos == "light_rj"
    assert info.confianca == const_mod.ATTR_CONFIANCA_MEDIA
    assert "fallback" in info.observacao.lower()
