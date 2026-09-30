"""Coordenador de atualização de um medidor White Box."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import WhiteboxClient, WhiteboxError
from .const import DOMAIN, MONTH_INTERVAL, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass
class WhiteboxData:
    """Última leitura: dados do dia e do mês."""

    day: dict[str, Any]
    month: dict[str, Any] | None


class WhiteboxCoordinator(DataUpdateCoordinator[WhiteboxData]):
    """Busca o dia a cada 5 min e o mês a cada 30 min."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: WhiteboxClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {client.code}",
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self._month: dict[str, Any] | None = None
        self._month_at: datetime | None = None

    async def _async_update_data(self) -> WhiteboxData:
        try:
            day = await self.client.fetch(0)
        except WhiteboxError as err:
            raise UpdateFailed(f"Erro ao ler o medidor: {err}") from err

        now = dt_util.utcnow()
        if self._month_at is None or now - self._month_at >= MONTH_INTERVAL:
            try:
                self._month = await self.client.fetch(1)
                self._month_at = now
            except WhiteboxError as err:
                # Mantém o último total do mês; os sensores do dia seguem funcionando.
                _LOGGER.warning("Erro ao ler o total do mês de %s: %s", self.client.code, err)

        return WhiteboxData(day=day, month=self._month)
