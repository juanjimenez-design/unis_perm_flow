"""
This is a boilerplate pipeline 'survival_model_presupuesto'
generated using Kedro 1.2.0
"""
"""
This is a boilerplate pipeline 'survival_model'
generated using Kedro 1.2.0
"""

import pandas as pd
from lifelines import CoxPHFitter

def preprocess_survival_data(df: pd.DataFrame, 
                             params: dict) -> pd.DataFrame:
    """Filtra y transforma los datos crudos de supervivencia en una matriz de diseño.

        Esta función limpia el dataset eliminando registros sin período inicial,
        estandariza los nombres de los programas académicos y genera de manera controlada 
        las variables de tipo dummy necesarias para el modelo de Cox en Python.
        Garantiza estabilidad en producción al forzar la existencia de todos los programas
        configurados en los parámetros (llenando con 0 si no hay estudiantes en el lote actual)
        y asegura que el programa de referencia se omita correctamente.

        Args:
            df (pd.DataFrame): Dataset crudo cargado desde el catálogo de Kedro 
                (ej: 'unis_estados_calac_survival') que contiene el histórico de estudiantes.
            params (dict): Diccionario de configuración inyectado desde `parameters.yml`.
                Debe contener las llaves:
                - 'programas_originales': list, todos los programas del catálogo base.
                - 'reference_program': str, el programa que actuará como base de comparación.
                - 'target_duration': str, nombre de la columna de tiempo (ej: 'month').
                - 'target_event': str, nombre de la columna del indicador de evento (ej: 'di').

        Returns:
            pd.DataFrame: Matriz de diseño balanceada (`df_cox`) lista para ser consumida 
                por el algoritmo de entrenamiento, conteniendo únicamente las columnas numéricas 
                de duración, evento y las variables dummy de los programas.
    """
    # 1. Filtrar valores nulos en periodo_inicial
    df_clean = df.copy() #df[df['periodo_inicial'].notna()].copy()
    
    # 2. Estandarizar nombres de los programas
    df_clean['programa'] = df_clean['programa'].astype(str).str.strip().str.lower()
    
    # 3. Generar dummies
    df_dummies = pd.get_dummies(df_clean['programa'], prefix='prog')
    
    # 4. Forzar que existan todos los programas del catálogo (así no tengan alumnos en este lote)
    programas = params['programas_originales']
    ref_program = params['reference_program']
    
    columnas_esperadas = [f'prog_{p}' for p in programas if p != ref_program]
    
    for col in columnas_esperadas:
        if col not in df_dummies.columns:
            df_dummies[col] = 0  # Si falta el programa, se llena con ceros
            
    # Garantizar que la referencia sea eliminada (por si get_dummies la creó)
    col_referencia = f'prog_{ref_program}'
    if col_referencia in df_dummies.columns:
        df_dummies = df_dummies.drop(columns=[col_referencia])
        
    # Ordenar y seleccionar estrictamente las columnas que el modelo espera
    df_dummies = df_dummies[columnas_esperadas]
    
    # 5. Unir dummies con las variables de tiempo y evento
    t_col = params['target_duration']
    e_col = params['target_event']
    
    df_cox = pd.concat([
        df_clean[[t_col, e_col]].reset_index(drop=True), 
        df_dummies.reset_index(drop=True)
    ], axis=1)
    
    # Asegurar tipos numéricos para lifelines
    for col in columnas_esperadas:
        df_cox[col] = df_cox[col].astype(int)
        
    return df_cox


def train_survival_model(df_cox: pd.DataFrame, 
                         params: dict) -> CoxPHFitter:
    
    """
        Ajusta un modelo de riesgos proporcionales de Cox utilizando lifelines.

        Toma la matriz de diseño procesada y entrena el objeto clasificador `CoxPHFitter`.
        Al finalizar el ajuste, el modelo queda listo para describir los Hazard Ratios de 
        cada programa o para ser exportado como un artefacto Pickle para futuras proyecciones.

        Args:
            df_cox (pd.DataFrame): Matriz de diseño limpia y numérica generada por el nodo 
                de preprocesamiento (`df_cox_preparado`).
            params (dict): Diccionario de configuración inyectado desde `parameters.yml`.
                Debe contener las llaves:
                - 'target_duration': str, columna que define el tiempo de seguimiento ('month').
                - 'target_event': str, columna del estado del estudiante ('di').

        Returns:
            CoxPHFitter: Objeto del modelo de supervivencia de Cox entrenado y serializable.
    """
    best_model = CoxPHFitter()
    best_model.fit(
        df_cox, 
        duration_col=params['target_duration'], 
        event_col=params['target_event']
    )
    return best_model