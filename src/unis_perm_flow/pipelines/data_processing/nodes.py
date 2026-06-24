"""
This is a boilerplate pipeline 'data_processing'
generated using Kedro 1.2.0
"""
"""
This is a boilerplate pipeline 'data_processing'
generated using Kedro 1.2.0
"""

"""
This is a boilerplate pipeline 'data_processing'
generated using Kedro 1.2.0
"""

import pandas as pd
import numpy as np
from datetime import datetime 
import duckdb
import unicodedata
import re
from typing import Tuple

def check_dataframe(data: pd.DataFrame) -> bool:
    """
    Check if the input data is a pandas DataFrame.

    Args:
        data: The input data to check.

    Returns:
        bool: True if data is a DataFrame, False otherwise.
    """
    return isinstance(data, pd.DataFrame)


def remove_accents(input_str):
    """
    Normaliza una cadena de texto eliminando acentos y caracteres especiales específicos.
    
    Pasos:
    1. Convierte a string y maneja nulos.
    2. Normaliza NFD para separar tildes de las letras.
    3. Elimina acentos/diéresis.

    Args:
        input_str: Cadena de texto original (ej. "Maestría en Educación (Virtual) - Cohorte 1.0")

    Returns:
        str: Cadena procesada (ej. "Maestria en Educacion Virtual  Cohorte 10")
    """
    if not isinstance(input_str, str):
        return input_str
    # Normalize to 'NFD' to separate characters from their accents
    nff_form = unicodedata.normalize('NFD', input_str)
    # Filter out the non-spacing mark (accents) and join back
    return "".join([char for char in nff_form if not unicodedata.combining(char)])

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean column names limpia los nombres de las columnas del DataFrame:
    1. Elimina acentos/diacríticos (á -> a, ñ
         -> n, etc.).
    2. Reemplaza caracteres no alfanuméricos por guiones bajos.
    3. Convierte a minúsculas.
    Args:
        df: El DataFrame con nombres de columnas a limpiar.
    Returns:
        pd.DataFrame: El DataFrame con nombres de columnas limpios.
    """
    # Apply accent removal to all column names first
    new_columns = [remove_accents(col) for col in df.columns]
    
    # Convert to Series to use vectorized string operations for the rest
    df.columns = (pd.Series(new_columns)
                  .str.strip()
                  .str.replace(r'[^a-zA-Z0-9]', '_', regex=True)
                  # Replace multiple underscores in a row with a single one (optional but cleaner)
                  .str.replace(r'_+', '_', regex=True)
                  .str.lower())
    
    return df

def select_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """Selecciona un subconjunto de columnas del DataFrame.
    Args:
        df: El DataFrame del cual seleccionar columnas.
        columns: Una lista de nombres de columnas a seleccionar.
    Returns:
        pd.DataFrame: Un nuevo DataFrame que contiene solo las columnas seleccionadas.
    
    """
    return df.loc[:, columns]

def convert_standardized_dates(df: pd.DataFrame, date_column: str) -> pd.DataFrame:
    """
    Convierte una columna de fechas que puede contener tanto fechas en formato string como números de serie de Excel.
    Args:
        df: El DataFrame que contiene la columna de fechas.
        date_column: El nombre de la columna que contiene las fechas a convertir.
    Returns:
        pd.DataFrame: El DataFrame con la columna de fechas convertida a formato datetime.
    """
    
    # 1. Convertir la columna date_columns a tipo numérico, forzando los errores a NaN
    numeric_check = pd.to_numeric(df[date_column], errors='coerce')
    # 2. Identificar filas que son números de serie de Excel (valores numéricos)
    df[date_column] = df[date_column].astype(str).str.replace('^202-', '2024-', regex=True)
    # 3. Convertir la columna date_column a datetime, manejando tanto strings como números de serie de Excel
    df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
    
    return df

def convert_all_standardized_dates(df: pd.DataFrame,
                                   date_columns: list) -> pd.DataFrame:
    """
    Convierte múltiples columnas de fechas en un DataFrame, manejando tanto strings como números de serie de Excel.
    Args:
        df: El DataFrame que contiene las columnas de fechas.
        date_columns: Una lista de nombres de columnas que contienen fechas.
    Returns:
        pd.DataFrame: El DataFrame con las columnas de fechas convertidas a formato datetime.
    """
    # 1. Iterar sobre cada columna de fecha y aplicar la función de conversión    
    for column in date_columns:
        df = convert_standardized_dates(df, column)
        
    return df

def clean_nulls(df: pd.DataFrame, subset: str or list) -> tuple:
    '''
    Limpia los valores nulos en un DataFrame basado en un subconjunto de columnas.
    Args:
        df: El DataFrame a limpiar.
        subset: Una columna o una lista de columnas para verificar los valores nulos.
    Returns:
        tuple: Un tuple que contiene el DataFrame limpio (sin nulos en el subset)
    '''
    df_nulls = df[df[subset].isna()]
    df_cleaned = df.dropna(subset=[subset])
    return df_cleaned, df_nulls

def numeric_conversion_node(df: pd.DataFrame, 
                            columns_list: list) -> pd.DataFrame:
    """ 
    Convierte las columnas especificadas a tipo numérico, manejando errores y valores faltantes.
    Args:
        df: El DataFrame que contiene las columnas a convertir.
        columns_list: Una lista de nombres de columnas que se deben convertir a numérico.
    Returns:
        pd.DataFrame: El DataFrame con las columnas convertidas a numérico y los valores faltantes manejados.
    """
    # 1. Convertir las columnas a numérico, forzando los errores a NaN
    df[columns_list] = df[columns_list].apply(pd.to_numeric, errors='coerce')
    
    # 2. Llenar los valores NaN con 0 (o cualquier otro valor que consideres apropiado)
    df[columns_list] = df[columns_list].fillna(0)
    
    return df


def remove_accents_and_special_chars(input_str: str, is_email: bool = False) -> str:
    """
        Normaliza texto eliminando acentos y caracteres especiales.

        Si `is_email` es True, preserva '@' y '.' para no romper la estructura del correo;
        de lo contrario, los elimina junto con el resto de la puntuación.

        Args:
            input_str (str): Cadena de texto original a procesar.
            is_email (bool): Indica si se deben proteger los símbolos de correo electrónico.

        Returns:
            str: Cadena normalizada, sin acentos y con espacios limpios.
    """
    if input_str is None or not isinstance(input_str, str):
        return input_str

    # 1. Normalización NFD para separar acentos
    nfd_form = unicodedata.normalize('NFD', input_str)
    
    # 2. Filtrar marcas de combinación (acentos)
    # Nota: Mantenemos la 'ñ' si prefieres, pero usualmente se filtra en NFD.
    text_without_accents = "".join(
        [char for char in nfd_form if not unicodedata.combining(char)]
    )

    # 3. Eliminar caracteres especiales
    if is_email:
        # Para correos: NO eliminamos '@' ni '.'
        # Eliminamos paréntesis y guiones (o lo que desees quitar de un email sucio)
        clean_text = re.sub(r'[()\-]', ' ', text_without_accents)
    else:
        # Para columnas normales: eliminamos todo incluyendo '.'
        clean_text = re.sub(r'[().\-]', ' ', text_without_accents)

    # 4. Limpieza de espacios
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

    return clean_text

def clean_column_objects(df: pd.DataFrame, email_cols: list = None) -> pd.DataFrame:
    """
    Limpia y estandariza columnas de tipo objeto en el DataFrame.

    Aplica conversión a minúsculas, eliminación de espacios y normalización de 
    caracteres. Permite identificar columnas de correo para proteger su formato 
    evitando la eliminación de '@' y '.'.

    Args:
        df (pd.DataFrame): DataFrame original con columnas de texto a procesar.
        email_cols (list, optional): Lista de nombres de columnas que deben 
            tratarse como correos electrónicos. Por defecto es None.

    Returns:
        pd.DataFrame: DataFrame con las columnas de tipo objeto normalizadas.
    """
    email_cols = email_cols or []
    
    for col in df.select_dtypes(include=['object']).columns:
        # Paso 1 y 2: Limpieza estándar
        df[col] = df[col].str.strip().str.lower()
        
        # Paso 3: Aplicar remoción diferenciada
        is_email = col in email_cols
        df[col] = df[col].apply(lambda x: remove_accents_and_special_chars(x, is_email=is_email))
        
    return df

def check_and_export_duplicates(
    df: pd.DataFrame, 
    subset: list, 
    col_ordenar: list
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Identifica duplicados y conserva únicamente el registro más reciente basado en un orden.

    Ordena el DataFrame según las columnas especificadas y separa los registros 
    duplicados en un DataFrame independiente, manteniendo el último registro del 
    orden en el DataFrame limpio.

    Args:
        df (pd.DataFrame): El DataFrame original a procesar.
        subset (list): Columnas que definen qué se considera un registro duplicado.
        col_ordenar (list): Columnas por las cuales ordenar (ej. fechas, versiones).

    Returns:
        tuple: (df_cleaned, duplicates)
            - df_cleaned: DataFrame sin duplicados (solo el registro más nuevo).
            - duplicates: DataFrame con todos los registros que fueron identificados como duplicados.
    """
    # 1. Ordenar el DataFrame para asegurar que el más nuevo quede al final
    # Usamos ascending=True para que el más reciente sea el último
    df_sorted = df.sort_values(by=subset + col_ordenar, ascending=True, na_position='first')

    # 2. Identificar todos los registros que tienen duplicados (para auditoría)
    # keep=False marca todas las ocurrencias
    duplicates = df_sorted[df_sorted.duplicated(subset=subset, keep=False)]

    # 3. Limpiar el DataFrame manteniendo solo el último registro (el más nuevo tras el sort)
    df_cleaned = df_sorted.drop_duplicates(subset=subset, keep='last')

    return df_cleaned, duplicates


#-----------------------------------------------------------------------------#
# Preprocess Calendario
#-----------------------------------------------------------------------------#


def unis_preprocessing_calaca(
    unis_calendario: pd.DataFrame,
    col_fechas: list,
    col_fechaingreso: str,
    col_fecha_ini_sem: str,
    col_fecha_fin_sem: str,
    col_cohorte_ini: str,
    col_sort: list,
    journey_labels: list,
    journey_thresholds: list,
    col_ordenadas: list
) -> pd.DataFrame:
    """
    Estandariza el calendario académico como línea de tiempo para el análisis de sobrevivencia.

    Transformaciones principales:
    1.  **Reloj Académico**: Calcula 'semana_acumulada' y 'month' relativo por cohorte (Tiempo T=0).
    2.  **Anclaje Temporal**: Identifica la 'fecha_ingreso' mínima por cohorte inicial.
    3.  **Ventanas de Eventos**: Genera 'shifted_fecha_inicio' para delimitar intervalos de riesgo.
    4.  **Estacionalidad**: Extrae 'month_gregoriano' para capturar efectos del calendario civil.
    5.  **Segmentación**: Clasifica el 'student_journey' según umbrales de meses parametrizados.

    Args:
        unis_calendario: Datos crudos de periodos y semanas.
        col_fechas/col_sort: Parámetros de limpieza y ordenamiento.
        journey_labels/thresholds: Lógica de negocio para etapas del estudiante.
        col_ordenadas: Estructura final de columnas según el catálogo.

    Returns:
        pd.DataFrame: Timeline enriquecida lista para cruce con eventos de baja.
        pd.DataFrame: Timeline enriquecida lista para cruce con eventos de baja hasta el día de hoy.

    """
    # 1. Limpieza inicial usando tus nodos base
    unis_calendario = clean_column_names(unis_calendario)
    unis_calendario = convert_all_standardized_dates(unis_calendario, date_columns=col_fechas)
    unis_calendario = clean_column_objects(unis_calendario)

    # 2. Calcular Fecha de ingreso (mínima fecha de inicio por cohorte)
    unis_calendario[col_fechaingreso] = (
        unis_calendario
        .groupby(col_cohorte_ini)[col_fecha_ini_sem]
        .transform('min')
    )

    # 3. Ordenar y calcular semanas acumuladas
    df_ext = unis_calendario.sort_values(by=col_sort).copy()
    df_ext['semana_acumulada'] = df_ext.groupby(col_fechaingreso).cumcount() + 1

    # 4. Calcular Mes Corrido y etiquetas
    df_ext['month'] = (df_ext['semana_acumulada'] - 1) // 4 + 1
    df_ext['mes_academico'] = 'm' + df_ext['month'].astype(str)

    # 5. Shift para obtener ventana de tiempo (inicio del siguiente bloque)
    df_ext['shifted_fecha_inicio'] = df_ext.groupby(col_cohorte_ini)[col_fecha_ini_sem].shift(-1)
    
    # Rellenar nulos con la fecha fin máxima de la cohorte
    df_ext['shifted_fecha_inicio'] = df_ext['shifted_fecha_inicio'].fillna(
        df_ext.groupby(col_cohorte_ini)[col_fecha_fin_sem].transform('max')
    )

    # 6. Definir Student Journey Dinámico
    # Construimos las condiciones automáticamente
    m2, m4 = journey_thresholds # Desempaquetamos los límites
    
    condiciones = [
        (df_ext['month'] > 0) & (df_ext['month'] <= m2), # onboarding
        (df_ext['month'] > m2) & (df_ext['month'] <= m4), # q1
        (df_ext['month'] > m4)                            # qa
    ]
    
    df_ext['student_journey'] = np.select(condiciones, journey_labels, default='unknown')

    # 7. Año y Mes gregoriano
    df_ext['mes_gregoriano'] = df_ext[col_fecha_fin_sem].dt.month
    df_ext['anio_gregoriano'] = df_ext[col_fecha_fin_sem].dt.year
     
    # 8. Orden de las columnas 
    df_ext = df_ext.loc[:, col_ordenadas]
    
    # 9. Calendario académico hasta la fecha actual
    mask_fechas_uptoday = df_ext[col_fecha_ini_sem] <= pd.Timestamp.now()
    df_ext_uptoday = df_ext.loc[mask_fechas_uptoday].copy()

    # 10. Calendario Académico hasta 09-2025
    date_presupuesto = datetime.strptime('2025-09-30', "%Y-%m-%d")
    mask_fechas_presupuesto = df_ext[col_fecha_ini_sem] <= date_presupuesto
    df_ext_uppresupuesto = df_ext.loc[mask_fechas_presupuesto].copy()

    return df_ext.reset_index(drop=True),df_ext_uptoday.reset_index(drop=True), df_ext_uppresupuesto.reset_index(drop=True), 


#-----------------------------------------------------------------------------#
# Preprocess Base Estado de estudiantes
#-----------------------------------------------------------------------------#

def unis_preprocessing_estaca(
    unis_estaca: dict,
    unis_col_fechas: list,
    unis_col_emails: list,
    unis_col_dd: list,
    unis_col_sort: list,
    unis_niveles_academicos: dict,
    unis_estaca_column_order: list
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Procesa, limpia y estandariza los datos maestros de estudiantes (ESTACA).

    Transformaciones principales:
    1.  **Limpieza y Tipificación**: Normaliza nombres de columnas, correos y asegura formato datetime.
    2.  **Agrupación Académica**: Homologa niveles (pregrado/posgrado) mediante mapeo paramétrico.
    3.  **Gestión de Calidad**: Identifica y separa registros duplicados para asegurar integridad en el análisis.
    4.  **Estructuración**: Ordena y filtra el dataset según la jerarquía definida en los parámetros.

    Args:
        unis_estaca: Diccionario de DataFrames (raw data).
        unis_col_fechas/emails/dd: Listas de columnas para normalización específica.
        unis_niveles_academicos: Diccionario de mapeo para niveles educativos.
        unis_estaca_column_order: Estructura final de columnas para el catálogo.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: 
            1. Dataset de estudiantes limpio y estandarizado.
            2. Dataset de registros duplicados o descartados para auditoría.
    """
    # 1. Limpieza de nombres de columnas (asumiendo que nodes.clean_column_names ya existe)
    # Si clean_column_names es un método importado, úsalo directamente:
    unis_estaca = unis_estaca['UNIS']
    unis_estaca = clean_column_names(unis_estaca)
    unis_estaca['identificacion'] = pd.to_numeric(unis_estaca['no_de_documento'], errors='coerce')
    unis_estaca.drop(columns= 'no_de_documento', inplace = True)
    unis_estaca['alianza'] = 'unis'
    # 2. Conversión de fechas estandarizadas
    unis_estaca = convert_all_standardized_dates(
        unis_estaca, 
        date_columns=unis_col_fechas
    )

    # 3. Limpieza de columnas de tipo objeto (emails)
    unis_estaca = clean_column_objects(
        unis_estaca, 
        email_cols=unis_col_emails
    )

    # 4. Verificación y exportación de duplicados
    # Retorna dos DataFrames: sd (sin duplicados) y cd (con duplicados)
    unis_estaca_sd, unis_estaca_cd = check_and_export_duplicates(
        unis_estaca, 
        subset=unis_col_dd, 
        col_ordenar=unis_col_sort
    )
    
    # 5. Indicadora de deserción
    mask_bajas = unis_estaca_sd['estado'].isin(['baja temporal', 'baja definitiva'])
    mask_bajas_definitiva = unis_estaca_sd['fecha_de_baja_d'].notna()
    mask_bajas_temporal = unis_estaca_sd['fecha_de_baja_t'].notna()
    unis_estaca_sd['di'] = np.where(mask_bajas & (mask_bajas_definitiva|mask_bajas_temporal) , 1, 0)
    # 6. Indicadora de graduación
    mask_graduados = unis_estaca_sd['estado'].isin(['egresado no graduado'])
    mask_fecha_graduados= unis_estaca_sd['fecha_de_grado'].notna()
    unis_estaca_sd['gi'] = np.where(mask_graduados & mask_fecha_graduados , 1, 0)
    # 7. Nivel académico
    unis_estaca_sd['nivel_academico'] = (
        unis_estaca_sd['nivel']
        .str.lower()
        .str.strip()
        .map(unis_niveles_academicos)
    )
    # 8. Creación de  la columna fecha ingreso
    unis_estaca_sd['fecha_ingreso'] = unis_estaca_sd['cohorte']
    unis_estaca_cd['fecha_ingreso'] = unis_estaca_cd['cohorte']
    # 9. Orden de las columnas
    unis_estaca_sd = unis_estaca_sd.loc[:,unis_estaca_column_order]
    
    return unis_estaca_sd, unis_estaca_cd

