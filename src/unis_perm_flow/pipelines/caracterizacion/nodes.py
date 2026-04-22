"""
This is a boilerplate pipeline 'caracterizacion'
generated using Kedro 1.2.0
"""
import pandas as pd
from pathlib import Path


# 2. Importar todas las funciones del archivo nodes.py
import unis_perm_flow.pipelines.data_processing.nodes as nodes


def transformar_caracterizacion_unis(
    df_caracterizacion: pd.DataFrame,
    df_estados_calac: pd.DataFrame,
    params_fechas: list,
    params_emails: list,
    params_duplicados: list,
    params_orden: list,
    params_columnas_caracterizacion: list
) -> pd.DataFrame:
    """
    Función para limpiar la base de operaciones y cruzarla con el calendario académico.
    """
    
    # 1. Limpieza de nombres de columnas
    df = nodes.clean_column_names(df_caracterizacion)
    
    # 2. Conversión de fechas usando los parámetros del YML
    df = nodes.convert_all_standardized_dates(df, params_fechas)
    
    # 3. Conversión de identidad a numérico (Coerce para manejar errores)
    df['identidad'] = pd.to_numeric(df['identidad'], errors='coerce')
    
    # 4. Limpieza de correos/objetos
    df = nodes.clean_column_objects(df, params_emails)
    
    # 5. Manejo de duplicados (obtenemos la base sin duplicados 'sd')
    df_sd, _ = nodes.check_and_export_duplicates(
        df, 
        subset=params_duplicados, 
        col_ordenar=params_orden
    )
    
    # 6. Eliminar columna 'nivel' si existe
    df_sd = df_sd.drop(columns='nivel', errors='ignore')

    # 7. Seleccionar columnas especificas
    df_sd = nodes.select_columns(df_sd, params_columnas_caracterizacion)

    
    # 8. Cruce con Calendario Académico (Merge)
    # Nota: Usamos df_sd para asegurar que el cruce no duplique filas inesperadamente
    resultado = df_estados_calac.merge(
        df_sd, 
        how='left', 
        left_on=['identificacion'], 
        right_on=['identidad']
    )
    
    return resultado