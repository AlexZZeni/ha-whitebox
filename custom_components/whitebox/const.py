"""Constantes da integração ISSO Digital White Box."""

from datetime import timedelta

DOMAIN = "whitebox"

CONF_CODE = "code"
CONF_LINK = "link"
CONF_SERIAL = "serial"

# O medidor grava uma amostra a cada 5 min; o total do mês muda devagar.
UPDATE_INTERVAL = timedelta(minutes=5)
MONTH_INTERVAL = timedelta(minutes=30)
