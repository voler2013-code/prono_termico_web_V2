"""Puente Python→SVG. Presión en hPa; temperatura en °C; altura en m s.n.m."""
import math
import statistics


def valido(x):
    return isinstance(x, (float, int)) and math.isfinite(x)


def mediana(xs):
    xs = [float(x) for x in xs if valido(x)]
    return statistics.median(xs) if xs else None


def presion_estandar(z_m):
    # MyUtils.AltitudeToPressure trabaja internamente en pies.
    return 1013.25 * (1 - (z_m / 0.3048) / 145366.45) ** (1 / 0.190284)


def crear_perfil(stats, elevacion, modelos, indices, levels, fecha, hora,
                  lugar, lat, lon, t2m, td2m, velocidades):
    def valores(variable):
        out = []
        for modelo, data in modelos.items():
            idx = indices.get(modelo)
            serie = data.get('hourly', {}).get(variable, [])
            if idx is not None and idx < len(serie) and valido(serie[idx]):
                out.append(serie[idx])
        return out

    p_superficie = mediana(valores('surface_pressure'))
    estimada = p_superficie is None
    if estimada:
        p_superficie = presion_estandar(elevacion)
    puntos = []
    for nivel, altura, var_t, var_rh in levels:
        if nivel == '2m':
            continue
        p = float(nivel.removesuffix('hPa'))
        if p >= p_superficie:
            continue  # niveles isobáricos situados debajo de la superficie
        z = mediana(valores('geopotential_height_' + nivel))
        if z is not None and z <= elevacion:
            continue
        st = stats.get(altura, {})
        t, td = st.get('T_mean'), st.get('Td_mean')
        if not valido(t) or not valido(td):
            continue
        n_t = len(valores(var_t))
        puntos.append(dict(p=p, t=t, td=td, z=z, z_ref=altura,
                           n=n_t, n_modelos=len(indices), interpolado=min(n_t, len(valores(var_rh))) < len(indices),
                           rh=st.get('RH_median'), sigma_t=st.get('T_std'),
                           v_empirica=velocidades.get(altura, {}).get('v_mean')))
    if valido(t2m) and valido(td2m):
        puntos.insert(0, dict(p=p_superficie, t=t2m, td=td2m, z=elevacion+2,
                              z_ref=elevacion+2, n=len(indices), superficie=True,
                              presion_estimada=estimada,
                              rh=stats.get(2, {}).get("RH_median")))
    return dict(fecha=fecha, hora=hora, lugar=lugar, lat=lat, lon=lon,
                elevacion=elevacion, modelos=list(indices), puntos=puntos,
                cobertura={m: sum(1 for n, _, vt, vr in levels if n != '2m'
                    and _dato(data, indices[m], vt) and _dato(data, indices[m], vr))
                    for m, data in modelos.items() if m in indices})


def limpiar(value):
    if isinstance(value, dict):
        return {k: limpiar(v) for k, v in value.items()}
    if isinstance(value, list):
        return [limpiar(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value



def _dato(data, idx, key):
    serie = data.get("hourly", {}).get(key, [])
    return isinstance(serie, list) and idx < len(serie) and valido(serie[idx])
