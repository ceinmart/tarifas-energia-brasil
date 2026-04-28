"""Versao: 0.1.0
Criado em: 2026-04-27 08:40:00 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path


def _install_homeassistant_stub() -> None:
    """Instala stubs minimos do Home Assistant para carregar __init__.py."""

    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    core = types.ModuleType("homeassistant.core")
    helpers = types.ModuleType("homeassistant.helpers")
    config_validation = types.ModuleType("homeassistant.helpers.config_validation")

    class ConfigEntry:
        pass

    class HomeAssistant:
        pass

    config_entries.ConfigEntry = ConfigEntry
    core.HomeAssistant = HomeAssistant
    config_validation.config_entry_only_config_schema = lambda domain: {"domain": domain}

    homeassistant.config_entries = config_entries
    homeassistant.core = core
    homeassistant.helpers = helpers
    helpers.config_validation = config_validation

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.config_validation"] = config_validation


def _load_init_module():
    base_dir = Path(__file__).resolve().parents[1] / "custom_components" / "tarifas_energia_brasil"
    package_name = "tarifas_energia_brasil_testpkg_init"
    package = types.ModuleType(package_name)
    package.__path__ = [str(base_dir)]  # type: ignore[attr-defined]
    sys.modules[package_name] = package

    const_module = types.ModuleType(f"{package_name}.const")
    const_module.CONF_HORAS_ATUALIZACAO = "frequencia_atualizacao_horas"
    const_module.HORAS_ATUALIZACAO_PADRAO = 24
    const_module.DOMAIN = "tarifas_energia_brasil"
    const_module.PLATFORMS = ["sensor"]
    sys.modules[f"{package_name}.const"] = const_module

    coordinator_module = types.ModuleType(f"{package_name}.coordinator")
    coordinator_module.TarifasEnergiaBrasilCoordinator = _FakeCoordinator
    sys.modules[f"{package_name}.coordinator"] = coordinator_module

    spec = importlib.util.spec_from_file_location(
        package_name,
        base_dir / "__init__.py",
        submodule_search_locations=[str(base_dir)],
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = module
    spec.loader.exec_module(module)
    return module


class _FakeCoordinator:
    """Coordinator fake que falha se setup bloquear no first_refresh."""

    instances: list[_FakeCoordinator] = []

    def __init__(self, hass, entry) -> None:  # noqa: ANN001
        self.hass = hass
        self.entry = entry
        self.started_tracking = False
        self.refreshed = False
        self.first_refresh_called = False
        self.state_loaded = False
        _FakeCoordinator.instances.append(self)

    async def async_ensure_state_loaded(self) -> None:
        self.state_loaded = True

    async def async_config_entry_first_refresh(self) -> None:
        self.first_refresh_called = True
        raise AssertionError("setup nao deve bloquear na primeira coleta externa")

    async def async_start_state_tracking(self) -> None:
        self.started_tracking = True

    async def async_refresh(self) -> None:
        self.refreshed = True


class _FakeConfigEntries:
    """Stub de config_entries do hass."""

    def __init__(self) -> None:
        self.forwarded: list[tuple[object, list[str]]] = []

    async def async_forward_entry_setups(self, entry, platforms) -> None:  # noqa: ANN001
        self.forwarded.append((entry, list(platforms)))


class _FakeHass:
    """Stub minimo do HomeAssistant para setup."""

    def __init__(self) -> None:
        self.data = {}
        self.config_entries = _FakeConfigEntries()
        self.tasks: list[asyncio.Task] = []

    def async_create_task(self, coro, name=None):  # noqa: ANN001
        task = asyncio.create_task(coro, name=name)
        self.tasks.append(task)
        return task


class _FakeEntry:
    """Stub minimo de ConfigEntry."""

    entry_id = "entry-1"
    options: dict = {}

    def __init__(self) -> None:
        self.unloads = []

    def async_on_unload(self, callback):  # noqa: ANN001
        self.unloads.append(callback)

    def add_update_listener(self, _listener):  # noqa: ANN001
        def _unsub() -> None:
            return None

        return _unsub


_install_homeassistant_stub()
init_module = _load_init_module()


def test_setup_entry_schedules_initial_refresh_without_blocking_setup():
    async def _run() -> None:
        result = await init_module.async_setup_entry(hass, entry)
        await asyncio.sleep(0)

        coordinator = _FakeCoordinator.instances[0]
        assert result is True
        assert coordinator.state_loaded is True
        assert coordinator.first_refresh_called is False
        assert coordinator.started_tracking is True
        assert coordinator.refreshed is True
        assert hass.config_entries.forwarded == [(entry, ["sensor"])]
        assert hass.data["tarifas_energia_brasil"][entry.entry_id] is coordinator
        assert len(hass.tasks) == 1
        assert hass.tasks[0].get_name() == "tarifas_energia_brasil_entry-1_initial_refresh"
        assert hass.tasks[0].cancel in entry.unloads

    _FakeCoordinator.instances.clear()
    hass = _FakeHass()
    entry = _FakeEntry()

    asyncio.run(_run())


def test_background_initial_refresh_swallows_runtime_errors():
    class BrokenCoordinator:
        async def async_refresh(self) -> None:
            raise RuntimeError("falha externa temporaria")

    asyncio.run(init_module._async_refresh_after_setup(BrokenCoordinator()))
