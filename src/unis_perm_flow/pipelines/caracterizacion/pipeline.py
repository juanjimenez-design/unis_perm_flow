"""
This is a boilerplate pipeline 'caracterizacion'
generated using Kedro 1.2.0
"""

from kedro.pipeline import Pipeline, node, pipeline
from .nodes import transformar_caracterizacion_unis

def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=transformar_caracterizacion_unis,
                inputs={
                    "df_caracterizacion": "unis_caracterizacion",
                    "df_estados_calac": "unis_estados_calac",
                    "params_fechas": "params:unis_caracterizacion_params.col_fechas",
                    "params_emails": "params:unis_caracterizacion_params.col_emails",
                    "params_duplicados": "params:unis_caracterizacion_params.col_dd",
                    "params_orden": "params:unis_caracterizacion_params.col_sort",
                    "params_columnas_caracterizacion": "params:unis_caracterizacion_params.params_columnas_caracterizacion"
                        },
                outputs="unis_estados_calac_crt", # Nombre del resultado
                name="nodo_transformar_caracterizacion_unis",
            ),
        ]
    )