"""
This is a boilerplate pipeline 'data_processing'
generated using Kedro 1.2.0
"""

from kedro.pipeline import Node, Pipeline, node, pipeline
from .nodes import unis_preprocessing_estaca,unis_preprocessing_calaca

def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [   node(
                func=unis_preprocessing_calaca,
                inputs={
                    "unis_calendario": "unis_calaca",
                    "col_fechas": "params:data_processing_calaca.unis_calaca_col_fechas",
                    "col_fechaingreso": "params:data_processing_calaca.unis_calaca_col_fechaingreso",
                    "col_fecha_ini_sem": "params:data_processing_calaca.unis_calaca_col_fecha_inicial_semana",
                    "col_fecha_fin_sem": "params:data_processing_calaca.unis_calaca_col_fecha_final_semana",
                    "col_cohorte_ini": "params:data_processing_calaca.unis_calaca_col_cohorte_inicial",
                    "col_sort": "params:data_processing_calaca.unis_calaca_col_sort",
                    "journey_labels": "params:data_processing_calaca.unis_calalaca_student_journey",
                    "journey_thresholds": "params:data_processing_calaca.unis_calaca_journey_thresholds",
                    "col_ordenadas": "params:data_processing_calaca.unis_calaca_column_order"
                },
                outputs=["unis_calendario_extendido","unis_calendario_extendido_uptoday","unis_calendario_extendido_presupuesto"],
                name="node_preprocessing_calaca"
            ),
            node(
                func=unis_preprocessing_estaca,
                inputs={
                    "unis_estaca": "unis_estaca", # Nombre de la tabla en el catálogo
                    "unis_col_fechas": "params:data_processing_estaca.unis_col_fechas",
                    "unis_col_emails": "params:data_processing_estaca.unis_col_emails",
                    "unis_col_dd": "params:data_processing_estaca.unis_col_dd",
                    "unis_col_sort": "params:data_processing_estaca.unis_col_sort",
                    "unis_niveles_academicos": "params:data_processing_estaca.unis_niveles_academicos",
                    "unis_estaca_column_order": "params:data_processing_estaca.unis_estaca_column_order",
                },
                outputs=["unis_estaca_sd", "unis_estaca_cd"],
                name="node_unis_preprocessing_estaca",
            ),
            node(
                func=unis_preprocessing_estaca,
                inputs={
                    "unis_estaca": "unis_estaca_presupuesto_completo", # Nombre de la tabla en el catálogo
                    "unis_col_fechas": "params:data_processing_estaca.unis_col_fechas",
                    "unis_col_emails": "params:data_processing_estaca.unis_col_emails",
                    "unis_col_dd": "params:data_processing_estaca.unis_col_dd",
                    "unis_col_sort": "params:data_processing_estaca.unis_col_sort",
                    "unis_niveles_academicos": "params:data_processing_estaca.unis_niveles_academicos",
                    "unis_estaca_column_order": "params:data_processing_estaca.unis_estaca_column_order",
                },
                outputs=["unis_estaca_sd_presupuesto", "unis_estaca_cd_presupuesto"],
                name="node_unis_preprocessing_estaca_presupuesto",
            ),
        ]
    )