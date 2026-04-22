"""
This is a boilerplate pipeline 'cascadas_lifetables_survival'
generated using Kedro 1.2.0
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime 
import duckdb
import unicodedata

# Funciones
def podar_tabla_vida(df: pd.DataFrame, dict_duracion: dict) -> pd.DataFrame:
    """
        Filtra el trayecto académico eliminando registros que superan la duración teórica.

        Aplica una búsqueda jerárquica de límites (Semanas) basada en Nivel y Programa,
        asegurando que el análisis de supervivencia se mantenga dentro de los límites
        institucionales definidos en el diccionario de configuración.

        Args:
            df: DataFrame con columnas 'nivel', 'programa' y 'semana_acumulada'.
            dict_duracion: Diccionario con topología {nivel: {programa: {semanas: int}}}.

        Returns:
            pd.DataFrame: Dataset filtrado por el límite de semanas correspondiente.
    """
    
    def obtener_limite(row):
        # Normalización robusta
        nivel = str(row['nivel']).lower().strip()
        programa = str(row['programa']).lower().strip()
        
        # Acceso seguro al diccionario
        nivel_dict = dict_duracion.get(nivel, {})
        
        # Prioridad 1: Programa específico
        if programa in nivel_dict:
            return nivel_dict[programa].get('semanas', float('inf'))
        
        # Prioridad 2: Default del nivel
        if 'default' in nivel_dict:
            return nivel_dict['default'].get('semanas', float('inf'))
        
        # Prioridad 3: Estructura plana (especialización)
        return nivel_dict.get('semanas', float('inf'))

    # Aplicamos el cálculo del límite
    df['limite_semanas'] = df.apply(obtener_limite, axis=1)
    
    # Filtrado: mantenemos solo lo que está dentro del rango
    df_podado = df[df['semana_acumulada'] <= df['limite_semanas']].copy()
    
    # Limpieza
    return df_podado.drop(columns=['limite_semanas'])


def generar_cascada_con_punto_cero(unis_count_nuevos, unis_calendario_extendido_uptoday):
    # 1. Crear el punto de partida (T=0)
    punto_cero = unis_count_nuevos.copy()
    
    punto_cero['fecha_inicio'] = punto_cero['fecha_ingreso']
    punto_cero['fecha_fin'] = punto_cero['fecha_ingreso']
    punto_cero['semana'] = 0
    punto_cero['semana_acumulada'] = 0
    punto_cero['month'] = 0
    punto_cero['mes_academico'] = 'm0'
    punto_cero['student_journey'] = 'ingreso'

    # 2. Tu merge original (El recorrido futuro de 1 a N)
    recorrido_futuro = pd.merge(
        unis_count_nuevos, 
        unis_calendario_extendido_uptoday[[
            'periodo_inicial', 'fecha_ingreso', 'fecha_inicio', 
            'fecha_fin', 'semana', 'semana_acumulada', 
            'month', 'mes_academico', 'student_journey'
        ]],
        on=['periodo_inicial', 'fecha_ingreso'],  
        how='left'
    )

    # 3. Concatenar el Punto Cero con el Recorrido
    # Usamos ignore_index=True para mantener el índice limpio
    cascadas_completa = pd.concat([punto_cero, recorrido_futuro], ignore_index=True)

    # 4. Ordenar para que el 'ingreso' (0) quede al principio de cada grupo
    cascadas_completa = cascadas_completa.sort_values(
        by=['periodo_inicial', 'programa', 'semana_acumulada']
    )

    return cascadas_completa



def aplicar_logica_semana_final(df, dict_niveles):
    """
    Identifica y marca como egresados no graduados (engi) a los estudiantes que 
    alcanzan el límite de duración teórica.

    Aplica una búsqueda jerárquica en el diccionario de configuración (Programa > Nivel Default)
    para determinar la semana límite. Si el estudiante sigue activo (ai) al llegar o 
    superar dicho umbral, su estado se transfiere a la columna 'engi'.

    Args:
        df (pd.DataFrame): Dataset con columnas 'nivel', 'programa', 'semana_acumulada' y 'ai'.
        dict_niveles (dict): Configuración de semanas límite por nivel y programa.

    Returns:
        pd.DataFrame: DataFrame actualizado con la columna 'engi' calculada y la auxiliar 'semana_limite'.
    """

    def obtener_semana_final(row):
        # Normalizamos los valores para evitar fallos por mayúsculas/minúsculas o espacios
        nivel = str(row['nivel']).lower().strip()
        programa = str(row['programa']).lower().strip()
        
        # 1. Caso Especialización (estructura plana)
        if nivel == 'especializacion':
            return dict_niveles['especializacion']['default']['semanas']
        
        # 2. Casos con excepciones (Maestría y Pregrado)
        if nivel in dict_niveles:
            config = dict_niveles[nivel]
            if programa in config:
                return config[programa]['semanas']
            else:
                return config.get('default', {}).get('semanas', np.nan)
        
        return np.nan

    # Calculamos la semana final para cada registro según el diccionario
    # Se crea una columna temporal 'semana_limite'
    df['semana_limite'] = df.apply(obtener_semana_final, axis=1)

    # Condición: si la 'semana_acumulada' (o 'semana') es igual o mayor a la semana_limite
    # Nota: Uso 'semana_acumulada' porque suele ser el indicador del progreso total.
    mask = df['semana_acumulada'] >= df['semana_limite']
    
    # Asignamos ci = estudiantes_activos donde se cumple la condición
    df.loc[mask, 'engi'] = df.loc[mask, 'ai']
    
    # Opcional: Eliminar la columna auxiliar para dejar el DF limpio
    # df.drop(columns=['semana_limite'], inplace=True)
    
    return df


def calcular_censuras_academica(df: pd.DataFrame, id_cols: list) -> pd.DataFrame:
    """
        Define y consolida los eventos de censura (ci) en el último punto de observación.

        Identifica el final del trayecto académico para cada registro y marca como censurados 
        aquellos estudiantes que permanecen activos (ai) o se graduaron (gi). Además, 
        reconstruye la población en riesgo (ni) basándose en el stock de activos del 
        periodo anterior.

        Args:
            df: DataFrame con el historial académico semanal.
            id_cols: Columnas que identifican de forma única al estudiante y su programa.

        Returns:
            pd.DataFrame: Dataset con ni recalculado y ci asignado al cierre de la observación.
    """
    # 1. Asegurar orden cronológico estricto
    df = df.sort_values(by=id_cols + [ 'semana_acumulada'])

    # 2. Identificar el último punto observado en la data para cada estudiante/programa
    # (Esto captura tanto a los que terminaron por 'poda' como a los que llegan a hoy)
    df['es_ultimo_punto'] = (
        df.groupby(id_cols)['semana_acumulada'].transform('max') == df['semana_acumulada']
    )

    # 3. ni (En Riesgo): Ya lo calculamos como el valor al inicio de la semana.
    # Si por alguna razón no viene en el DF, ni es el 'ai' del periodo anterior.
    # (Asumimos que ya tienes 'ni' del paso anterior, si no, descomenta la siguiente línea)
    df['ni'] = df.groupby(id_cols)['ai'].shift(1).fillna(df['nuevos'])

    # 4. di (Eventos - Bajas):
    # Usamos el 'di' que ya calculaste (conteo de identificaciones con baja).
    # IMPORTANTE: En el último punto observado, no registramos bajas nuevas 
    # porque no podemos confirmar si ocurrió el evento o se acabó el tiempo de observación.
    #df['di_final'] = np.where(~df['es_ultimo_punto'], df['di'], 0)

    # 5. ci (Censuras):
    # Son los estudiantes que permanecen activos (ai) en el último punto 
    # observado del dataset. 
    df['ci'] = np.where(df['es_ultimo_punto'], df['ai'] + df['gi'], 0)

    # 6. Limpieza y preparación final
    # Eliminamos columnas auxiliares para no ensuciar el catálogo
    columnas_finales = df.drop(columns=['es_ultimo_punto'])
    
    return columnas_finales


def calcular_km_y_eti_dinamico(
    df: pd.DataFrame, 
    group_cols: list, 
    unidades_tiempo:list,
    conf_z: float = 1.96
) -> tuple:
    """
    Calcula el estimador de Kaplan-Meier y la Eficiencia Terminal (ETI) de forma dinámica.

    Esta función procesa un panel de datos semanal para generar una tabla de vida académica, 
    gestionando la población en riesgo (ni) y las salidas (bajas y censuras). Implementa 
    correcciones para evitar el inflado de la población inicial y asegurar que la ETI 
    se mantenga dentro de límites lógicos.

    Lógica Principal:
    1. Agregación Dinámica: Consolida eventos (di, gi, engi, ci) y stock (ai) por grupos. 
       Usa transformaciones para mantener la población 'nuevos' constante.
    2. Cálculo de Riesgo (ni): Reconstruye la exposición inicial de cada semana sumando 
       activos finales más todas las salidas del periodo (di + ci).
    3. Kaplan-Meier: Estima la probabilidad de supervivencia acumulada (km) y su error 
       estándar mediante la fórmula de Greenwood.
    4. Eficiencia Terminal (ETI): Calcula la proporción de activos sobre una población 
       neta (ajustada por censuras previas), restringiendo el resultado a valores <= 1.0 
       y evitando crecimientos artificiales respecto a la semana anterior.

    Args:
        df: DataFrame con métricas base (ai, di, gi, engi, ci, nuevos).
        group_cols: Columnas para la agrupación (ej:  'programa').
        conf_z: Valor Z para el intervalo de confianza (por defecto 1.96 para 95%).

    Returns:
        pd.DataFrame: Tabla de vida con métricas de flujo, acumulados, supervivencia 
                      con intervalos de confianza y eficiencia terminal.
    """
    # 1. Agregación dinámica
    # Para 'nuevos', usamos max() porque el valor es constante por cohorte
    # Para ai, usamos sum() porque representa el stock de esa semana
    # Para di, gi, engi, ci, usamos sum() para consolidar eventos de la semana
    df_agrupado = (
        df.groupby(group_cols + unidades_tiempo)
        .agg({
            'ai': 'sum',
            'di': 'sum',
            'gi': 'sum',
            'engi': 'sum',
            'ci': 'sum',
            'nuevos': 'sum' # <--- CAMBIO CRÍTICO: No sumar valores repetidos
        })
        .reset_index()
    )

    # 2. Ordenar cronológicamente
    df_agrupado = df_agrupado.sort_values(by=group_cols + unidades_tiempo)

    # 3. n_total dinámico
    # Si agrupamos por 'programa', sumamos los máximos de cada cohorte (si existieran)
    # o simplemente tomamos el máximo si el grupo es la cohorte misma.
    df_agrupado['n_total'] = df_agrupado.groupby(group_cols)['nuevos'].transform('max')

    # 4. Cálculo de ni (En riesgo)
    # n_i = activos_final + censuras_final + bajas_final
    df_agrupado['ni'] = df_agrupado['ai'] + df_agrupado['ci'] + df_agrupado['di']
    df_agrupado['ni'] = df_agrupado['ni'].clip(lower=0)

    # 5. Agrupación para métricas de probabilidad
    grouped = df_agrupado.groupby(group_cols)

    # 6. Kaplan-Meier (Supervivencia)
    df_agrupado['qi'] = np.where(df_agrupado['ni'] > 0, df_agrupado['di'] / df_agrupado['ni'], 0)
    df_agrupado['pi'] = 1 - df_agrupado['qi']
    df_agrupado['km'] = grouped['pi'].cumprod()

    # 7. Greenwood (Varianza e Intervalos)
    mask = (df_agrupado['ni'] > df_agrupado['di']) & (df_agrupado['ni'] > 0)
    df_agrupado['greenwood_term'] = np.where(
        mask, 
        df_agrupado['di'] / (df_agrupado['ni'] * (df_agrupado['ni'] - df_agrupado['di'])), 
        0
    )
    df_agrupado['km_se'] = np.sqrt(df_agrupado['km']**2 * grouped['greenwood_term'].cumsum())
    df_agrupado['km_ic_inf'] = (df_agrupado['km'] - (conf_z * df_agrupado['km_se'])).clip(0, 1)
    df_agrupado['km_ic_sup'] = (df_agrupado['km'] + (conf_z * df_agrupado['km_se'])).clip(0, 1)

    # 8. ETI (Eficiencia Terminal)
    # gi_engi_prev: Acumulado de ci (que incluye graduados/egresados) hasta la semana anterior
    ci_cum = grouped['ci'].cumsum()
    gi_engi_prev = grouped['ci'].transform(lambda x: x.cumsum().shift(0).fillna(0))
    
    df_agrupado['nuevos'] = df_agrupado['n_total']
    denominador_eti = df_agrupado['n_total'] - gi_engi_prev
    df_agrupado['n_total'] = df_agrupado['n_total'] - gi_engi_prev
    df_agrupado['eti'] = np.where(denominador_eti > 0, df_agrupado['ai'] / denominador_eti, 0)
    # Calculamos la ETI cruda
    eti_cruda = np.where(denominador_eti > 0, df_agrupado['ai'] / denominador_eti, 0)

    # Obtenemos la ETI de la semana anterior por grupo
    eti_anterior = grouped['eti'].shift(1).fillna(1.0) 

    # Si la ETI cruda es mayor que 1 (o mayor que la anterior, según tu regla), 
    # se queda con el valor anterior.
    # Nota: Usamos clip(upper=1) para asegurar que nunca exceda el 100%
    df_agrupado['eti'] = np.where(eti_cruda > 1.0, eti_anterior, eti_cruda)

    # Cifras acumuladas
    df_agrupado['ci_cum'] = gi_engi_prev
    df_agrupado['di_cum'] =  grouped['di'].transform(lambda x: x.cumsum().shift(0).fillna(0))
    df_agrupado['gi_cum'] =  grouped['gi'].transform(lambda x: x.cumsum().shift(0).fillna(0))

    # Selección final de columnas
    cols_finales = group_cols + unidades_tiempo + ['nuevos', 'n_total', 'ni', 'ai','di','di_cum', 'gi', 'gi_cum', 'engi', 'ci','ci_cum',
        'qi', 'pi', 'km', 'km_se', 'km_ic_inf', 'km_ic_sup', 'eti'
    ]
    
    df_agrupado = df_agrupado.sort_values( by = group_cols + unidades_tiempo)
    return df_agrupado[cols_finales].reset_index(drop=True)

#----------------------------------------------------------------------
#  crear_cascada_supervivencia
#----------------------------------------------------------------------

def crear_cascada_supervivencia(
    unis_estados_calac: pd.DataFrame,
    unis_calendario_extendido_uptoday: pd.DataFrame,
    unis_bajas_calendario_academico: pd.DataFrame,
    unis_graduados_calendario_academico: pd.DataFrame,
    dict_niveles_duracion: dict,
    params: dict
) -> pd.DataFrame:
    """
    Nodo que integra ingresos, bajas, graduados y aplica lógica de censura académica.
    """
    
    # 1. Conteo de Nuevos (Punto Cero)
    unis_count_nuevos = (
        unis_estados_calac.loc[:, params['group_columnas_agrupacion'] + ['identificacion']]
        .groupby(params['group_columnas_agrupacion'])
        .agg(nuevos=('identificacion', 'count'))
        .reset_index()
        .sort_values(by=['fecha_ingreso', 'nuevos'], ascending=[True, False])
    )

    # Generar cascada inicial (Asumiendo que esta función está importada o definida)
    cascadas_inicial_calendario = generar_cascada_con_punto_cero(
        unis_count_nuevos, 
        unis_calendario_extendido_uptoday
    )

    # 2. Integración de Bajas (di)
    unis_count_bajas = (
        unis_bajas_calendario_academico.loc[:, params['columnas_agrupacion'] + ['di']]
        .groupby(params['columnas_agrupacion'])
        .agg({'di': 'sum'})
        .reset_index()
        .sort_values(by=params['columnas_to_order'], ascending=True)
    )

    cascadas_semanal = pd.merge(
        cascadas_inicial_calendario,
        unis_count_bajas[params['columnas_agrupacion'] + ['di']],
        on=params['columnas_agrupacion'],
        how='left'
    ).fillna({'di': 0})

    # 3. Integración de Graduados (gi)
    unis_count_graduados = (
        unis_graduados_calendario_academico.loc[:, params['columnas_agrupacion'] + ['gi']]
        .groupby(params['columnas_agrupacion'])
        .agg({'gi': 'sum'})
        .reset_index()
        .sort_values(by=params['columnas_to_order'], ascending=True)
    )

    cascadas_semanal = pd.merge(
        cascadas_semanal,
        unis_count_graduados[params['columnas_agrupacion'] + ['gi']],
        on=params['columnas_agrupacion'],
        how='left'
    ).fillna({'gi': 0})

    # 4. Poda del calendario según duración teórica
    cascadas_semanal_podada = podar_tabla_vida(cascadas_semanal, dict_niveles_duracion)

    # 5. Cálculo de Acumulados y Activos (ai)
    # Agrupamos por las columnas base de la cohorte/programa
    group_base = ['fecha_ingreso','nivel', 'programa']
    
    cascadas_semanal_podada['di_cum'] = cascadas_semanal_podada.groupby(group_base)['di'].cumsum()
    cascadas_semanal_podada['gi_cum'] = cascadas_semanal_podada.groupby(group_base)['gi'].cumsum()

    # Estudiantes activos al final de la semana
    cascadas_semanal_podada['ai'] = (
        cascadas_semanal_podada['nuevos'] - 
        cascadas_semanal_podada['di_cum'] - 
        cascadas_semanal_podada['gi_cum']
    )

    # 6. Lógica de Semana Final y Egresados (engi)
    cascadas_semanal_podada = aplicar_logica_semana_final(
        cascadas_semanal_podada, 
        dict_niveles_duracion
    )
    
    # Ajuste de engi (evitar doble conteo con graduados)
    mask_engi = cascadas_semanal_podada['engi'] >= cascadas_semanal_podada['gi']
    cascadas_semanal_podada.loc[mask_engi, 'engi'] = (
        cascadas_semanal_podada.loc[mask_engi, 'engi'] - 
        cascadas_semanal_podada.loc[mask_engi, 'gi']
    )
    cascadas_semanal_podada['engi'] = cascadas_semanal_podada['engi'].fillna(0)

    # 7. Cálculo final de Censuras (ci)
    cascadas_semanal_final = calcular_censuras_academica(
        cascadas_semanal_podada, 
        params['group_columnas_agrupacion']
    )

    return cascadas_semanal_final.loc[:, params['columnas_tokeep']]


# Mensual

def crear_cascada_supervivencia_mensual(df: pd.DataFrame, 
                                        group_columns: list):
    """
        Consolida la granularidad temporal de las cascadas de semanal a mensual.

        Este nodo realiza una reducción de datos aplicando una lógica de agregación 
        heterogénea basada en la naturaleza de cada indicador:
        - Límites temporales: Preserva el rango mediante 'min' y 'max'.
        - Indicadores de estado (Stock): Mantiene niveles críticos usando 'min' y 'max'.
        - Variables de flujo (Acumulados): Totaliza volúmenes mediante 'sum'.

        Args:
            df (pd.DataFrame): Dataset de cascadas con granularidad semanal.
            group_columns (list): Columnas de agrupación (ej. IDs, dimensiones y 
                                la referencia temporal mensual).

        Returns:
            pd.DataFrame: Resumen mensual con las métricas consolidadas e índice reseteado.
    """
    
    # Definición del diccionario de agregación
    agg_rules = {
        'fecha_inicio': 'min',
        'fecha_fin': 'max',
        'nuevos': 'max',
        'ai': 'min',
        'di': 'sum',
        'gi': 'sum',
        'engi': 'sum',
        'ci': 'sum'
    }
    
    # Ejecución de la lógica
    df_result = (
        df
        .groupby(group_columns)
        .agg(agg_rules)
        .reset_index()
    )
    
    return df_result