from pathlib import Path

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.whitebox.api import BASE_URL, extract_code
from custom_components.whitebox.const import CONF_CODE, CONF_SERIAL, DOMAIN

FIXTURES = Path(__file__).parent / "fixtures"
CODE = "6DZCJXC2L8DY"
DATA_URL = f"{BASE_URL}/essentials/data/"


def mock_meter(aioclient_mock, code=CODE):
    aioclient_mock.get(DATA_URL, params={"per": "0", "gran": "0", "sid": code}, text=(FIXTURES / "day.json").read_text())
    aioclient_mock.get(DATA_URL, params={"per": "0", "gran": "1", "sid": code}, text=(FIXTURES / "month.json").read_text())
    aioclient_mock.get(f"{BASE_URL}/{code}/", text=(FIXTURES / "page.html").read_text())


def test_extract_code():
    assert extract_code(f"https://whitebox.isso.digital/{CODE}/") == CODE
    assert extract_code(f"  {CODE} ") == CODE
    assert extract_code("https://whitebox.isso.digital/") is None


async def test_config_flow_creates_entry(hass: HomeAssistant, aioclient_mock):
    mock_meter(aioclient_mock)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"link": f"https://whitebox.isso.digital/{CODE}/", "name": "Ar-condicionado"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Ar-condicionado"
    assert result["data"] == {CONF_CODE: CODE, CONF_SERIAL: "353A42C83159"}


async def test_config_flow_invalid_code(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.get(DATA_URL, params={"per": "0", "gran": "0", "sid": "AAAAAAAAAAAA"}, status=302)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"link": "AAAAAAAAAAAA", "name": "X"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_code"}


async def test_config_flow_invalid_link(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"link": "abc", "name": "X"})
    assert result["errors"] == {"link": "invalid_link"}


async def test_setup_creates_device_and_sensors(hass: HomeAssistant, aioclient_mock):
    mock_meter(aioclient_mock)
    entry = MockConfigEntry(
        domain=DOMAIN, title="Ar-condicionado", unique_id=CODE,
        data={CONF_CODE: CODE, CONF_SERIAL: "353A42C83159"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1
    device = devices[0]
    assert (DOMAIN, CODE) in device.identifiers
    assert device.name == "Ar-condicionado"
    assert device.manufacturer == "ISSO Digital"
    assert device.serial_number == "353A42C83159"

    entities = er.async_entries_for_device(er.async_get(hass), device.id)
    assert len(entities) == 27

    states = {e.entity_id: hass.states.get(e.entity_id) for e in entities}
    for entity_id, state in states.items():
        float(state.state)  # todas as leituras presentes
        print(entity_id, state.state, state.attributes.get("unit_of_measurement"))

    assert hass.states.get("sensor.ar_condicionado_energy_today").attributes["unit_of_measurement"] == "kWh"

    assert await hass.config_entries.async_unload(entry.entry_id)
