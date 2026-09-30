# ISSO Digital White Box para Home Assistant

Integração personalizada que lê medidores de energia da [ISSO Digital](https://isso.digital) pelo link
público do painel White Box (`https://whitebox.isso.digital/XXXXXXXXXXXX/`) e cria um **dispositivo** por
medidor, com 27 sensores.

> Usa o mesmo endpoint da interface "Essentials" do painel público. Não é uma API oficial: se a ISSO mudar o
> site ou revogar o link, a integração para de funcionar.

## Sensores

| Grandeza | Sensores |
|---|---|
| Energia | consumo hoje (kWh, zera à meia-noite), consumo do mês |
| Tensão | fases A, B, C |
| Corrente | fases A, B, C, neutro |
| Potência ativa | fases A, B, C, total |
| Potência aparente | fases A, B, C, total (soma vetorial) |
| Potência reativa | fases A, B, C, total (soma vetorial) |
| Fator de potência | fases A, B, C, médio |
| Outros | frequência da rede, temperatura do medidor (diagnóstico) |

O dia é lido a cada 5 min (o ritmo do medidor) e o total do mês a cada 30 min.

## Instalação (HACS)

1. HACS → menu ⋮ → **Repositórios personalizados** → cole a URL deste repositório, categoria **Integração**.
2. Procure **ISSO Digital White Box** no HACS, instale e reinicie o Home Assistant.
3. **Configurações → Dispositivos e serviços → Adicionar integração → ISSO Digital White Box**.
4. Cole o link público do medidor e dê um nome (ex.: "Ar-condicionado"). Repita para cada medidor.

## Painel Energia

Em **Configurações → Painéis → Energia → Consumo da rede elétrica**, adicione o sensor **Consumo hoje** de
cada medidor. Se um medidor estiver a jusante de outro, use **Consumo de dispositivos individuais** para o
de baixo. Não use o **Consumo mês** no painel Energia.

## Desenvolvimento

```sh
python -m venv venv && ./venv/bin/pip install pytest-homeassistant-custom-component
./venv/bin/pytest
```
