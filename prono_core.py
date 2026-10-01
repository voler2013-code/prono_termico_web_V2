# -*- coding: utf-8 -*-
"""
Script: prono_termico3.py
Pronóstico térmico usando Open-Meteo Customer API.
Modelos: icon_seamless, gfs_seamless, meteofrance_seamless, ecmwf_ifs,
         ukmo_seamless, gem_seamless, cma_grapes_global

AL ACABARSE LA API PAGA HAY QUE VOLVER A LA GRATIS EL CODIGO, Y ESTA FUNCIONA MAS A LA NOCHE CON MENOS CONGESTION

Descripción:
  - Interpreta una consulta flexible tipo: "hoy; 15hs; cuchi" o
    "01-12-2025; 14hs; -31,55; -64,33; -9; 25"
  - Llama a múltiples modelos de Open-Meteo.
  - Maximiza la resolución vertical agregando niveles intermedios.
  - Interpola linealmente los datos faltantes por modelo.
  - Calcula medianas y desviaciones estándar por altura.
  - Calcula punto de rocío y velocidad térmica.
  - Dibuja un sondeo ASCII con pendientes basadas en ΔT_normalizada,
    sin logaritmos, imitando un diagrama skew‑T.

"""

import sys
import os
import re
import math
import shutil
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Any

import requests
import numpy as np
from datetime import timezone
from skewt_data import crear_perfil

def hoy_argentina():
    return datetime.now(timezone(timedelta(hours=-3))).date()

TZ = "America/Argentina/Buenos_Aires"  # UTC-3 todo el año, sin horario de verano

# ---------------------------------------------------------------------
# Ancho del sondeo ASCII: se adapta a la terminal para no cortar línea.
# ---------------------------------------------------------------------
# En Termux (terminal real) se detecta el ancho automáticamente. En Pydroid 3
# la consola no es una terminal real y no reporta su ancho, así que se usa
# un valor por defecto conservador (44) que entra en una pantalla de celular
# en vertical sin hacer salto de línea.
#
# Se puede forzar un ancho distinto con una variable de entorno, por ejemplo:
#   PRONO_ANCHO=60 python prono.py "sj; hoy; 15hs"
ANCHO_SONDEO_DEFAULT = 80

# Compensación para Pydroid 3: su fuente monoespaciada ocupa más píxeles
# horizontalmente que la de Telegram. Un valor menor comprime el eje X sin
# cambiar los datos meteorológicos ni la separación vertical.
ESCALA_SONDEO_DEFAULT = Decimal("3.3")

# Compresión horizontal del dibujo.
# 2 = aproximadamente la mitad del ancho actual.
COMPRESION_HORIZONTAL = 2

def determinar_escala_sondeo() -> Decimal:
    """Escala horizontal en caracteres por unidad de temperatura.
    En Pydroid 3 se usa 3.3 para compensar su fuente más ancha.
    Se puede ajustar con PRONO_ESCALA (ej. 3.2 o 3.4).
    """
    env_val = os.environ.get("PRONO_ESCALA")
    if env_val:
        try:
            valor = Decimal(env_val.replace(",", "."))
            if valor > 0:
                return valor
        except Exception:
            pass
    return ESCALA_SONDEO_DEFAULT

def determinar_ancho_sondeo() -> int:
    env_val = os.environ.get("PRONO_ANCHO")
    if env_val:
        try:
            return max(20, int(env_val))
        except ValueError:
            pass

    try:
        columnas = shutil.get_terminal_size(fallback=(ANCHO_SONDEO_DEFAULT, 20)).columns
        if columnas and columnas != 80:  # 80 suele ser el "no sé", no un valor real
            return max(20, columnas - 1)  # -1 de margen para no cortar justo al borde
    except Exception:
        pass

    return ANCHO_SONDEO_DEFAULT

# NOTA: se usa la API GRATUITA de Open-Meteo (sin apikey, sin plan pago).
# El plan pago que se usaba antes (customer-api.open-meteo.com) requiere el
# plan Professional o superior para acceder al Historical Forecast API.

LUGARES: Dict[str, Tuple[float, float]] = {
    "merlo": (-32.34, -64.98),
    "trasla": (-31.72, -65.00),
    "ped": (-31.76, -64.65),
    "alpina": (-32.02, -64.81),
    "sj": (-31.32, -64.34),
    "cuchi": (-30.99, -64.71),
    "rioja": (-29.40, -66.82),
    "tuc": (-26.77, -65.28),
}

LEVELS = [
    ("2m", 2, "temperature_2m", "relative_humidity_2m"),
    ("1000hPa", 110, "temperature_1000hPa", "relative_humidity_1000hPa"),
    ("975hPa", 320, "temperature_975hPa", "relative_humidity_975hPa"),
    ("950hPa", 500, "temperature_950hPa", "relative_humidity_950hPa"),
    ("925hPa", 800, "temperature_925hPa", "relative_humidity_925hPa"),
    ("900hPa", 1000, "temperature_900hPa", "relative_humidity_900hPa"),
    ("875hPa", 1200, "temperature_875hPa", "relative_humidity_875hPa"),
    ("850hPa", 1500, "temperature_850hPa", "relative_humidity_850hPa"),
    ("825hPa", 1700, "temperature_825hPa", "relative_humidity_825hPa"),
    ("800hPa", 1900, "temperature_800hPa", "relative_humidity_800hPa"),
    ("775hPa", 2200, "temperature_775hPa", "relative_humidity_775hPa"),
    ("750hPa", 2500, "temperature_750hPa", "relative_humidity_750hPa"),
    ("725hPa", 2700, "temperature_725hPa", "relative_humidity_725hPa"),
    ("700hPa", 3000, "temperature_700hPa", "relative_humidity_700hPa"),
    ("675hPa", 3300, "temperature_675hPa", "relative_humidity_675hPa"),
    ("650hPa", 3600, "temperature_650hPa", "relative_humidity_650hPa"),
    ("625hPa", 3900, "temperature_625hPa", "relative_humidity_625hPa"),
    ("600hPa", 4200, "temperature_600hPa", "relative_humidity_600hPa"),
    ("575hPa", 4500, "temperature_575hPa", "relative_humidity_575hPa"),
    ("550hPa", 4900, "temperature_550hPa", "relative_humidity_550hPa"),
    ("525hPa", 5200, "temperature_525hPa", "relative_humidity_525hPa"),
    ("500hPa", 5600, "temperature_500hPa", "relative_humidity_500hPa"),
    ("475hPa", 6000, "temperature_475hPa", "relative_humidity_475hPa"),
    ("450hPa", 6300, "temperature_450hPa", "relative_humidity_450hPa"),
    ("425hPa", 6800, "temperature_425hPa", "relative_humidity_425hPa"),
    ("400hPa", 7200, "temperature_400hPa", "relative_humidity_400hPa"),
    ("375hPa", 7600, "temperature_375hPa", "relative_humidity_375hPa"),
    ("350hPa", 8100, "temperature_350hPa", "relative_humidity_350hPa"),
    ("325hPa", 8600, "temperature_325hPa", "relative_humidity_325hPa"),
    ("300hPa", 9200, "temperature_300hPa", "relative_humidity_300hPa"),
    ("275hPa", 9700, "temperature_275hPa", "relative_humidity_275hPa"),
    ("250hPa", 10400, "temperature_250hPa", "relative_humidity_250hPa"),
]

def construir_lista_variables_desde_levels() -> List[str]:
    vars_out: List[str] = []
    vistos = set()

    for _, _, var_T, var_RH in LEVELS:
        for var in (var_T, var_RH):
            if var not in vistos:
                vars_out.append(var)
                vistos.add(var)

    return vars_out

TODAS_LAS_VARIABLES = construir_lista_variables_desde_levels()
TODAS_LAS_VARIABLES += ["surface_pressure"] + [
    "geopotential_height_" + nivel for nivel, _, _, _ in LEVELS if nivel != "2m"
]

# ---------------------------------------------------------------------
# Modelos meteorológicos consultados.
# Todos solicitan el mismo set completo de variables (TODAS_LAS_VARIABLES).
# Los niveles que un modelo no entregue nativamente (o entregue como null)
# se completan luego vía interpolación vertical en interpolar_niveles_faltantes().
# ---------------------------------------------------------------------
MODELOS: Dict[str, Dict[str, List[str]]] = {
    "icon_seamless": {
        "vars": TODAS_LAS_VARIABLES.copy()
    },
    "gfs_seamless": {
        "vars": TODAS_LAS_VARIABLES.copy()
    },
    "meteofrance_seamless": {
        "vars": TODAS_LAS_VARIABLES.copy()
    },
    "ecmwf_ifs": {
        "vars": TODAS_LAS_VARIABLES.copy()
    },
    "ukmo_seamless": {
        "vars": TODAS_LAS_VARIABLES.copy()
    },
    "gem_seamless": {
        "vars": TODAS_LAS_VARIABLES.copy()
    },
    "cma_grapes_global": {
        "vars": TODAS_LAS_VARIABLES.copy()
    },
}

# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------

def parse_float(token: str) -> Optional[float]:
    token = token.strip()
    token = token.replace(" ", "").replace(",", ".")

    m = re.fullmatch(r"[+-]?\d+(?:\.\d+)?", token)
    if not m:
        return None

    try:
        return float(token)
    except ValueError:
        return None

def detectar_fecha(token: str) -> Optional[date]:
    t = token.strip().lower()
    hoy = hoy_argentina()

    if t == "hoy":
        return hoy

    if t == "ayer":
        return hoy - timedelta(days=1)

    if t in {"mañ", "mañana", "man", "mana", "manana"}:
        return hoy + timedelta(days=1)

    t2 = t.replace(" ", "")

    if re.fullmatch(r"\d{2}-\d{2}-\d{4}", t2):
        try:
            d, m, y = map(int, t2.split("-"))
            return date(y, m, d)
        except Exception:
            return None

    return None

def detectar_hora(token: str) -> Optional[int]:
    t = token.strip().lower().replace(" ", "")
    m = re.fullmatch(r"(\d{1,2})hs", t)

    if not m:
        return None

    hh = int(m.group(1))

    if 0 <= hh <= 23:
        return hh

    return None

def detectar_lugar(token: str) -> Optional[Tuple[str, Tuple[float, float]]]:
    t = token.strip().lower()

    if t in LUGARES:
        return t, LUGARES[t]

    return None

def armar_fecha_str(d: date) -> str:
    return d.strftime("%Y-%m-%d")

def construir_url(
    lat: float,
    lon: float,
    fecha: date,
    modelo: str,
    vars_list: List[str]
) -> str:
    hourly = ",".join(vars_list)
    hoy = hoy_argentina()

    es_historico = fecha < hoy - timedelta(days=14)

    # API GRATUITA de Open-Meteo: el dominio cambia según el tipo de dato, y
    # el path siempre es "/v1/forecast" (sin apikey).
    #   - Reciente/futuro:  api.open-meteo.com/v1/forecast
    #   - Histórico:        historical-forecast-api.open-meteo.com/v1/forecast
    host = "historical-forecast-api.open-meteo.com" if es_historico else "api.open-meteo.com"

    return (
        f"https://{host}/v1/forecast?"
        f"latitude={lat}"
        f"&longitude={lon}"
        f"&hourly={hourly}"
        f"&models={modelo}"
        f"&timezone={requests.utils.quote(TZ)}"
        f"&start_date={armar_fecha_str(fecha)}"
        f"&end_date={armar_fecha_str(fecha)}"
        f"&format=json"
    )

def valor_valido(x: Any) -> bool:
    if x is None:
        return False

    try:
        xf = float(x)
    except Exception:
        return False

    return math.isfinite(xf)

def dewpoint_from_T_RH(T: float, RH: float) -> Optional[float]:
    if T is None or RH is None:
        return None

    if not valor_valido(T) or not valor_valido(RH):
        return None

    if RH <= 0:
        return None

    try:
        return float(T) + 35.0 * math.log10(float(RH) / 100.0)
    except Exception:
        return None

# Cache de datos por lugar/fecha/modelo. Permite consultar varias horas
# en una misma consulta sin volver a descargar los mismos datos.
_FETCH_CACHE: Dict[Tuple[float, float, date, str, Tuple[str, ...]], Optional[dict]] = {}

def fetch_model_data(
    lat: float,
    lon: float,
    fecha: date,
    modelo: str,
    vars_list: List[str]
) -> Optional[dict]:
    cache_key = (
        round(float(lat), 6),
        round(float(lon), 6),
        fecha,
        modelo,
        tuple(vars_list),
    )

    if cache_key in _FETCH_CACHE:
        return _FETCH_CACHE[cache_key]

    url = construir_url(lat, lon, fecha, modelo, vars_list)

    try:
        r = requests.get(url, timeout=30)

        if r.status_code != 200:
            _FETCH_CACHE[cache_key] = None
            return None

        data = r.json()
        _FETCH_CACHE[cache_key] = data
        return data

    except Exception:
        _FETCH_CACHE[cache_key] = None
        return None

def find_hour_index(times: List[str], target_hour: int) -> Optional[int]:
    for i, ts in enumerate(times):
        try:
            hh = int(ts[11:13])
            if hh == target_hour:
                return i
        except Exception:
            continue

    return None

def round_half_up(x: Any) -> int:
    return int(
        Decimal(str(x)).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    )

# ---------------------------------------------------------------------
# Interpolación vertical
# ---------------------------------------------------------------------

def interpolar_niveles_faltantes(
    por_altura: Dict[int, Dict[str, List[Tuple[str, float]]]]
) -> None:
    alturas = sorted({altura_m for _, altura_m, _, _ in LEVELS})
    variables = ("T", "RH", "Td")

    modelos = set()

    for altura_m in alturas:
        if altura_m not in por_altura:
            continue

        for var in variables:
            for modelo, val in por_altura[altura_m].get(var, []):
                if modelo != "custom" and valor_valido(val):
                    modelos.add(modelo)

    for modelo in sorted(modelos):
        for var in variables:
            valores_por_altura: Dict[int, float] = {}

            for altura_m in alturas:
                entradas = por_altura.get(altura_m, {}).get(var, [])

                for modelo_dato, val in entradas:
                    if modelo_dato == modelo and valor_valido(val):
                        valores_por_altura[altura_m] = float(val)
                        break

            if len(valores_por_altura) < 2:
                continue

            alturas_validas = sorted(valores_por_altura.keys())

            for h in alturas:
                if h in valores_por_altura:
                    continue

                inferiores = [ha for ha in alturas_validas if ha < h]
                superiores = [ha for ha in alturas_validas if ha > h]

                if not inferiores or not superiores:
                    continue

                h_inf = max(inferiores)
                h_sup = min(superiores)

                if h_sup == h_inf:
                    continue

                v_inf = valores_por_altura[h_inf]
                v_sup = valores_por_altura[h_sup]

                v_interp = v_inf + ((h - h_inf) / (h_sup - h_inf)) * (v_sup - v_inf)

                if var == "RH":
                    v_interp = max(0.0, min(100.0, v_interp))

                por_altura[h][var].append((modelo, float(v_interp)))

    for altura_m in alturas:
        T_por_modelo = {
            modelo: val
            for modelo, val in por_altura[altura_m].get("T", [])
            if modelo != "custom" and valor_valido(val)
        }

        RH_por_modelo = {
            modelo: val
            for modelo, val in por_altura[altura_m].get("RH", [])
            if modelo != "custom" and valor_valido(val)
        }

        Td_por_modelo = {
            modelo: val
            for modelo, val in por_altura[altura_m].get("Td", [])
            if modelo != "custom" and valor_valido(val)
        }

        for modelo in sorted(set(T_por_modelo) & set(RH_por_modelo)):
            if modelo in Td_por_modelo:
                continue

            Td = dewpoint_from_T_RH(
                float(T_por_modelo[modelo]),
                float(RH_por_modelo[modelo])
            )

            if Td is not None:
                por_altura[altura_m]["Td"].append((modelo, float(Td)))

# ---------------------------------------------------------------------
# Núcleo de procesamiento
# ---------------------------------------------------------------------

def procesar_consulta(query: str):
    tokens = [t.strip() for t in query.split(";") if t.strip() != ""]

    fecha: Optional[date] = None
    hora: Optional[int] = None
    lugar_nombre: Optional[str] = None
    coords: Optional[Tuple[float, float]] = None
    td_custom: Optional[float] = None
    t_custom: Optional[float] = None

    numeric_positions: List[Tuple[int, float]] = []
    hora_explicita = False

    for idx, tok in enumerate(tokens):
        if fecha is None:
            f = detectar_fecha(tok)
            if f is not None:
                fecha = f
                continue

        if not hora_explicita:
            h = detectar_hora(tok)
            if h is not None:
                hora = h
                hora_explicita = True
                continue

        if lugar_nombre is None and coords is None:
            lug = detectar_lugar(tok)
            if lug is not None:
                lugar_nombre, coords = lug[0], lug[1]
                continue

        val = parse_float(tok)
        if val is not None:
            numeric_positions.append((idx, val))

    # Nueva forma: "sj; hoy; 9; 12; 13; 14; 15".
    # Con lugar+fecha y sin una hora escrita con "hs", los números restantes
    # son horarios si todos son enteros entre 0 y 23.
    if (
        fecha is not None
        and coords is not None
        and lugar_nombre is not None
        and not hora_explicita
        and numeric_positions
        and all(float(v).is_integer() and 0 <= int(v) <= 23
                for _, v in numeric_positions)
    ):
        horas = sorted(dict.fromkeys(int(v) for _, v in numeric_positions))
        if len(horas) > 1:
            for i, h in enumerate(horas):
                procesar_consulta(
                    f"{lugar_nombre}; {fecha.strftime('%d-%m-%Y')}; {h:02d}hs"
                )
                if i < len(horas) - 1:
                    print()
            return
        if len(horas) == 1:
            hora = horas[0]
            numeric_positions = []

    # Se mantiene el comportamiento anterior para coordenadas y Td/T personalizados.
    used_indices = set()

    def try_assign_pair(i1: int, v1: float, i2: int, v2: float) -> Optional[str]:
        nonlocal coords, td_custom, t_custom

        if coords is None and (-90.0 <= v1 <= 90.0) and (-180.0 <= v2 <= 180.0):
            coords = (v1, v2)
            return "coords"

        if td_custom is None and t_custom is None:
            td_custom, t_custom = v1, v2
            return "tdt"

        return None

    numeric_positions.sort(key=lambda x: x[0])

    i = 0
    while i < len(numeric_positions) - 1:
        idx1, v1 = numeric_positions[i]
        idx2, v2 = numeric_positions[i + 1]

        if idx2 == idx1 + 1 and idx1 not in used_indices and idx2 not in used_indices:
            assigned = try_assign_pair(idx1, v1, idx2, v2)
            if assigned:
                used_indices.update({idx1, idx2})
                i += 2
                continue
        i += 1

    # Validar los datos obligatorios después de interpretar todos los tokens.
    missing = []
    if fecha is None:
        missing.append("fecha")
    if hora is None:
        missing.append("horario, formato 24hs, ej. 15hs")
    if coords is None:
        missing.append("lugar o coordenadas, lat; lon")

    if missing:
        print("Falta ingresar: " + ", ".join(missing))
        return

    lat, lon = coords

    modelos_data: Dict[str, dict] = {}
    elevation_values: List[float] = []

    for modelo, meta in MODELOS.items():
        data = fetch_model_data(lat, lon, fecha, modelo, meta["vars"])

        if data:
            modelos_data[modelo] = data

            if "elevation" in data and valor_valido(data["elevation"]):
                elevation_values.append(float(data["elevation"]))

    if not modelos_data:
        print("No se pudo obtener datos de Open-Meteo para esa consulta.")
        return

    elevation = float(np.nanmedian(elevation_values)) if elevation_values else float("nan")

    if not valor_valido(elevation):
        elevation = 0.0

    hour_index_by_model: Dict[str, int] = {}

    for modelo, data in modelos_data.items():
        times = data.get("hourly", {}).get("time", [])
        idx = find_hour_index(times, hora)

        if idx is not None:
            hour_index_by_model[modelo] = idx

    if not hour_index_by_model:
        print("No se encontró la hora solicitada en los datos devueltos.")
        return

    por_altura: Dict[int, Dict[str, List[Tuple[str, float]]]] = {}

    for _, altura_m, _, _ in LEVELS:
        por_altura[altura_m] = {
            "T": [],
            "RH": [],
            "Td": []
        }

    for modelo, data in modelos_data.items():
        idx = hour_index_by_model.get(modelo)

        if idx is None:
            continue

        hourly = data.get("hourly", {})

        for _, altura_m, var_T, var_RH in LEVELS:
            T_list = hourly.get(var_T)
            RH_list = hourly.get(var_RH)

            T = T_list[idx] if isinstance(T_list, list) and idx < len(T_list) else None
            RH = RH_list[idx] if isinstance(RH_list, list) and idx < len(RH_list) else None

            if valor_valido(T):
                por_altura[altura_m]["T"].append((modelo, float(T)))

            if valor_valido(RH):
                RH_float = max(0.0, min(100.0, float(RH)))
                por_altura[altura_m]["RH"].append((modelo, RH_float))
                RH = RH_float

            if valor_valido(T) and valor_valido(RH) and float(RH) > 0:
                Td = dewpoint_from_T_RH(float(T), float(RH))

                if Td is not None:
                    por_altura[altura_m]["Td"].append((modelo, float(Td)))

    interpolar_niveles_faltantes(por_altura)

    stats_por_altura: Dict[int, Dict[str, float]] = {}

    for altura_m, dct in por_altura.items():
        T_vals = [float(v) for _, v in dct["T"] if valor_valido(v)]
        RH_vals = [float(v) for _, v in dct["RH"] if valor_valido(v)]
        Td_vals = [float(v) for _, v in dct["Td"] if valor_valido(v)]

        stats_por_altura[altura_m] = {
            "T_mean": float(np.nanmedian(T_vals)) if T_vals else float("nan"),
            "T_std": float(np.nanstd(T_vals, ddof=0)) if T_vals else float("nan"),
            "RH_median": float(np.nanmedian(RH_vals)) if RH_vals else float("nan"),
            "RH_std": float(np.nanstd(RH_vals, ddof=0)) if RH_vals else float("nan"),
            "Td_mean": float(np.nanmedian(Td_vals)) if Td_vals else float("nan"),
            "Td_std": float(np.nanstd(Td_vals, ddof=0)) if Td_vals else float("nan"),
        }

    td2m_out = td_custom if td_custom is not None else stats_por_altura[2]["Td_mean"]
    t2m_out = t_custom if t_custom is not None else stats_por_altura[2]["T_mean"]
    rh2m_out = stats_por_altura[2]["RH_median"]

    def veloc_termica(RocioTermica: float, Rocio: float, Temp: float) -> Optional[float]:
        try:
            num = (1.1 ** abs(RocioTermica - Rocio)) - 1.0
            den = 1.1 ** abs(Temp - Rocio)

            if den <= 0:
                return None

            return 5.6 * math.sqrt(max(0.0, num / den))

        except Exception:
            return None

    alturas_ordenadas = [h for h in sorted(por_altura.keys()) if h > elevation]
    v_stats_por_altura: Dict[int, Dict[str, float]] = {}

    td2m_por_modelo: Dict[str, float] = {}

    for modelo, val in por_altura[2]["Td"]:
        if valor_valido(val):
            td2m_por_modelo[modelo] = float(val)

    if td_custom is not None:
        for modelo in modelos_data.keys():
            td2m_por_modelo[modelo] = float(td_custom)

    if not td2m_por_modelo and valor_valido(stats_por_altura[2]["Td_mean"]):
        for modelo in modelos_data.keys():
            td2m_por_modelo[modelo] = stats_por_altura[2]["Td_mean"]

    for idx_alt, altura_m in enumerate(alturas_ordenadas):
        v_vals: List[float] = []

        T_por_modelo = {
            m: v
            for m, v in por_altura[altura_m]["T"]
            if m != "custom" and valor_valido(v)
        }

        Td_por_modelo = {
            m: v
            for m, v in por_altura[altura_m]["Td"]
            if m != "custom" and valor_valido(v)
        }

        for modelo in modelos_data.keys():
            Td2m = td2m_por_modelo.get(modelo)
            Td_h = Td_por_modelo.get(modelo)
            T_h = T_por_modelo.get(modelo)

            if Td_h is None and valor_valido(stats_por_altura[altura_m]["Td_mean"]):
                Td_h = stats_por_altura[altura_m]["Td_mean"]

            if T_h is None and valor_valido(stats_por_altura[altura_m]["T_mean"]):
                T_h = stats_por_altura[altura_m]["T_mean"]

            if Td2m is None or Td_h is None or T_h is None:
                continue

            if not valor_valido(Td2m) or not valor_valido(Td_h) or not valor_valido(T_h):
                continue

            RocioTermica = (
                Td2m
                if idx_alt == 0
                else Td2m - ((altura_m - elevation) * 0.0018)
            )

            v = veloc_termica(float(RocioTermica), float(Td_h), float(T_h))

            if v is not None and valor_valido(v):
                v_vals.append(v)

        if v_vals:
            v_stats_por_altura[altura_m] = {
                "v_mean": float(np.nanmedian(v_vals)),
                "v_std": float(np.nanstd(v_vals, ddof=0)),
            }
        else:
            v_stats_por_altura[altura_m] = {
                "v_mean": float("nan"),
                "v_std": float("nan"),
            }

    lugar_str = lugar_nombre if lugar_nombre else f"{lat:.2f},{lon:.2f}"
    cabecera = f"{'m':<5}   {'P.R':<4}   {'T':<4}   {'H%':<5}   m/s"

    hoy = hoy_argentina()

    if fecha == hoy:
        fecha_etq = "hoy"
    elif fecha == hoy - timedelta(days=1):
        fecha_etq = "ayer"
    elif fecha == hoy + timedelta(days=1):
        fecha_etq = "mañ"
    else:
        fecha_etq = fecha.strftime("%d-%m-%Y")

    print("Prono térmico para:")
    print(f"{fecha_etq}; {hora:02d}hs; {lugar_str}; {int(round(elevation))}m")
    print()
    print(cabecera)

    alturas_out = sorted(alturas_ordenadas, reverse=True)

    def fmt_int(x: Optional[float]) -> str:
        return "" if x is None or not valor_valido(x) else f"{int(round(float(x)))}"

    def fmt_rh(x: Optional[float]) -> str:
        return "" if x is None or not valor_valido(x) else f"{int(round(float(x)))}%"

    def fmt_v(v: Optional[float], vs: Optional[float]) -> str:
        if v is None or not valor_valido(v):
            return ""

        if vs is None or not valor_valido(vs):
            return f"{float(v):.1f}"

        return f"{float(v):.1f}±{float(vs):.1f}"

    def fmt_row(
        altura: int,
        td: Optional[float],
        t: Optional[float],
        rh: Optional[float],
        v: Optional[float],
        vs: Optional[float]
    ) -> str:
        td_str = fmt_int(td)
        t_str = fmt_int(t)
        rh_str = fmt_rh(rh)
        v_str = fmt_v(v, vs)

        return f"{altura:>4}   {td_str:<4}   {t_str:<4}   {rh_str:<5}   {v_str}"

    for h in alturas_out:
        stats_h = stats_por_altura.get(h, {})
        v_h = v_stats_por_altura.get(h, {})

        print(
            fmt_row(
                h,
                stats_h.get("Td_mean"),
                stats_h.get("T_mean"),
                stats_h.get("RH_median"),
                v_h.get("v_mean"),
                v_h.get("v_std"),
            )
        )

    print(
        fmt_row(
            int(round(elevation)),
            td2m_out,
            t2m_out,
            rh2m_out,
            0.0,
            0.0
        )
    )

    print()

    # La tabla original se imprime; los datos numéricos del gráfico viajan al worker.
    # Ya no se construye ni se interpreta un gráfico ASCII.
    return crear_perfil(
        stats_por_altura, elevation, modelos_data, hour_index_by_model,
        LEVELS, fecha.isoformat(), hora, lugar_str, lat, lon,
        t2m_out, td2m_out, v_stats_por_altura
    )

# ---------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        consulta = " ".join(sys.argv[1:])
    else:
        consulta = input("Ingrese consulta, ej: 'hoy; 15hs; cuchi': ")

    try:
        procesar_consulta(consulta)

    except KeyboardInterrupt:
        print("\nCancelado por el usuario.")

    except Exception as e:
        print("Error inesperado:", str(e))