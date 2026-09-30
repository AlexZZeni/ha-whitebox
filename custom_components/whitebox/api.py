"""Cliente do painel público ISSO Digital White Box.

Usa o endpoint da interface "Essentials", o mesmo que a página pública consome.
Não é uma API oficial: se o site mudar, é aqui que a integração quebra.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import aiohttp

BASE_URL = "https://whitebox.isso.digital"

_CODE_RE = re.compile(r"\b([A-Z0-9]{12})\b")
_PRESET_RE = re.compile(r"DATA_PRESET\s*=\s*(\{.*?\});")
_SERIAL_RE = re.compile(r"\(([0-9A-F]{12})\)")
_TIMEOUT = aiohttp.ClientTimeout(total=30)


class WhiteboxError(Exception):
    """Erro genérico ao falar com o White Box."""


class WhiteboxConnectionError(WhiteboxError):
    """Falha de rede ou resposta inesperada."""


class WhiteboxInvalidCode(WhiteboxError):
    """O código do link público não existe ou foi revogado."""


def extract_code(text: str) -> str | None:
    """Extrai o código de 12 caracteres de um link ou do próprio código."""
    match = _CODE_RE.search(text.strip())
    return match.group(1) if match else None


def series_last(data: dict[str, Any], key: str, name: str) -> float | None:
    """Último valor da série `name` da grandeza `key`."""
    for series in data.get("GraficosTelemetria", {}).get(key, []):
        if series.get("name") == name and series.get("data"):
            return float(series["data"][-1][1])
    return None


def total_consumption(data: dict[str, Any] | None) -> float | None:
    """Consumo acumulado (kWh) do período consultado."""
    try:
        return float(data["Totais"][0]["Consumo"])  # type: ignore[index]
    except (TypeError, KeyError, IndexError, ValueError):
        return None


class WhiteboxClient:
    """Acesso a um medidor pelo código do link público."""

    def __init__(self, session: aiohttp.ClientSession, code: str) -> None:
        self._session = session
        self.code = code

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> aiohttp.ClientResponse:
        try:
            resp = await self._session.get(
                f"{BASE_URL}{path}", params=params, timeout=_TIMEOUT, allow_redirects=False
            )
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise WhiteboxConnectionError(str(err)) from err
        # Código desconhecido redireciona para a tela de login.
        if resp.status in (301, 302, 303):
            resp.release()
            raise WhiteboxInvalidCode(self.code)
        if resp.status != 200:
            resp.release()
            raise WhiteboxConnectionError(f"HTTP {resp.status}")
        return resp

    async def fetch(self, granularity: int) -> dict[str, Any]:
        """Dados do período atual: 0 = dia, 1 = mês."""
        resp = await self._get(
            "/essentials/data/", {"per": 0, "gran": granularity, "sid": self.code}
        )
        try:
            data = await resp.json(content_type=None)
        except (aiohttp.ClientError, ValueError) as err:
            raise WhiteboxConnectionError(f"Resposta inválida: {err}") from err
        if not isinstance(data, dict) or not data.get("Sucesso"):
            raise WhiteboxInvalidCode(self.code)
        return data

    async def fetch_info(self) -> dict[str, str]:
        """Título e número de série, lidos da página pública (melhor esforço)."""
        resp = await self._get(f"/{self.code}/")
        html = await resp.text()
        match = _PRESET_RE.search(html)
        if not match:
            return {}
        try:
            title = json.loads(match.group(1)).get("Titulo", "")
        except ValueError:
            return {}
        info = {"title": title}
        if serial := _SERIAL_RE.search(title):
            info["serial"] = serial.group(1)
        return info
