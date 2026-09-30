"""Fluxo de configuração: o usuário cola o link público do medidor."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WhiteboxClient, WhiteboxError, WhiteboxInvalidCode, extract_code
from .const import CONF_CODE, CONF_LINK, CONF_SERIAL, DOMAIN

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LINK): str,
        vol.Required(CONF_NAME): str,
    }
)


class WhiteboxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Adiciona um medidor White Box."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            code = extract_code(user_input[CONF_LINK])
            if code is None:
                errors[CONF_LINK] = "invalid_link"
            else:
                await self.async_set_unique_id(code)
                self._abort_if_unique_id_configured()
                client = WhiteboxClient(async_get_clientsession(self.hass), code)
                try:
                    await client.fetch(0)
                    info = await client.fetch_info()
                except WhiteboxInvalidCode:
                    errors["base"] = "invalid_code"
                except WhiteboxError:
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data={CONF_CODE: code, CONF_SERIAL: info.get("serial")},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(STEP_USER_SCHEMA, user_input),
            errors=errors,
        )
