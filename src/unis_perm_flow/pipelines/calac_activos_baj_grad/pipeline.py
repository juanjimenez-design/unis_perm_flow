"""
This is a boilerplate pipeline 'calac_activos_baj_grad'
generated using Kedro 1.2.0
"""


# from kedro.pipeline import Node, Pipeline, node, pipeline
# from .nodes import momento_baja,\
#                    momento_grado,\
#                    momento_activos,\
#                    consolidar_estados_calac,\
#                    generate_train_coxph_forecast


# def create_pipeline(**kwargs) -> Pipeline:
#     return pipeline(
#         [node(
#             func=momento_baja,
#             inputs={
#                 "unis_estaca_sd": "unis_estaca_sd",
#                 "unis_col_fechadef": "params:bajas_calac.unis_col_fechadef",
#                 "unis_col_fechatemp": "params:bajas_calac.unis_col_fechatemp",
#                 "dict_duracion": "params:graduados_calac.dict_niveles_duracion",
#                 "unis_calaca": "unis_calendario_extendido_uptoday",
#                 "fallback_weeks": "params:graduados_calac.graduation_fallback_weeks",
#                 "left_on": "params:bajas_calac.merge_left_on", # 'fecha_baja'
#                 "right_on": "params:bajas_calac.merge_right_on", # 'fecha_inicio'
#                 "group_key": "params:bajas_calac.unis_calaca_col_cohorte_inicial",
#                 "sort_cols": "params:bajas_calac.unis_calaca_col_sort",
#             },
#             outputs="unis_bajas_calendario_academico",
#             name="node_momento_baja"
#         ),
#         node(
#                 func=momento_grado,
#                 inputs={
#                     "unis_estaca": "unis_estaca_sd",
#                     "unis_calaca": "unis_calendario_extendido_uptoday",
#                     "dict_duracion": "params:graduados_calac.dict_niveles_duracion",
#                     "col_gi": "params:graduados_calac.graduation_col_gi",
#                     "fallback_weeks": "params:graduados_calac.graduation_fallback_weeks",
#                     "join_left": "params:graduados_calac.graduation_join_keys_left",
#                     "join_right": "params:graduados_calac.graduation_join_keys_right",
#                 },
#                 outputs="unis_graduados_calendario_academico",
#                 name="node_momento_graduacion"
#             ),
#         node(
#                 func=momento_activos,
#                 inputs={
#                     "unis_estaca": "unis_estaca_sd",              # Dataset maestro
#                     "unis_calaca": "unis_calendario_extendido_uptoday",   # Maestro calendario
#                     "dict_duracion": "params:graduados_calac.dict_niveles_duracion", # Reutilizamos dict
#                     "col_di": "params:activos_calac.col_di",            # 'di'
#                     "col_gi": "params:activos_calac.col_gi",            # 'gi'
#                     "fallback_weeks": "params:graduados_calac.graduation_fallback_weeks",
#                     "join_left": "params:activos_calac.join_keys_left",  # 'fecha_activo'
#                     "join_right": "params:activos_calac.join_keys_right",# 'fecha_inicio'
#                     "group_key": "params:activos_calac.group_key",       # 'cohorte_inicial'
#                 },
#                 outputs="unis_activos_calendario",
#                 name="nodo_momento_activos",
#             ),
#             node(
#             func=consolidar_estados_calac,
#             inputs=[
#                 "unis_bajas_calendario_academico",
#                 "unis_graduados_calendario_academico",
#                 "unis_activos_calendario",
#                 "params:orden_columnas_universo",
#             ],
#             outputs="unis_estados_calac",
#             name="nodo_consolidar_estados_calac"
#         ),
#         node(
#             func=generate_train_coxph_forecast,
#             inputs=[
#                 "unis_estados_calac",
#                 "params:col_survival",
#             ],
#             outputs="unis_estados_calac_survival",
#             name="nodo_generate_train_coxph_forecast"
#         ),
#     ]
#     )

import logging
log = logging.getLogger(__name__)
import os
from pathlib import Path
from kedro.config import OmegaConfigLoader          # Kedro >= 0.18
from kedro.framework.project import settings  
from kedro.pipeline import Node, Pipeline, node, pipeline
from .nodes import (
    consolidar_estados_calac,
    generate_train_coxph_forecast,
    momento_activos,
    momento_baja,
    momento_grado,
)


def create_pipeline(**kwargs) -> Pipeline:
    # 1. Nombres base de los datasets (Tal cual corren hoy)
    estaca = "unis_estaca_sd"
    calendario = "unis_calendario_extendido_uptoday"
    
    out_bajas = "unis_bajas_calendario_academico"
    out_graduados = "unis_graduados_calendario_academico"
    out_activos = "unis_activos_calendario"
    out_estados = "unis_estados_calac"
    out_survival = "unis_estados_calac_survival"

    # 2. Capturamos el parámetro desde la consola
    # conf_loader = OmegaConfigLoader(
    #     conf_source=str(Path.cwd() / settings.CONF_SOURCE),
    #     base_env="base",
    #     default_run_env="local",
    # )

    # params: dict = conf_loader["parameters"]
    # ejecutar_presupuesto = params.get("ejecutar_presupuesto", False)
    ejecutar_presupuesto = os.getenv("PRESUPUESTO", "false").lower() == "true"

    # 3. Si se activa la bandera, agregamos los sufijos automáticamente
    if ejecutar_presupuesto:
        estaca = f"{estaca}_presupuesto"                  # -> unis_estaca_sd_presupuesto
        calendario = "unis_calendario_extendido_presupuesto" # -> Tu nombre del catálogo
        
        out_bajas = f"{out_bajas}_presupuesto"            # -> unis_bajas_calendario_academico_presupuesto
        out_graduados = f"{out_graduados}_presupuesto"    # -> unis_graduados_calendario_academico_presupuesto
        out_activos = f"{out_activos}_presupuesto"        # -> unis_activos_calendario_presupuesto
        out_estados = f"{out_estados}_presupuesto"        # -> unis_estados_calac_presupuesto
        out_survival = f"{out_survival}_presupuesto"      # -> unis_estados_calac_survival_presupuesto

    # 4. Tu plantilla de pipeline usando las variables dinámicas
    return pipeline(
        [
            node(
                func=momento_baja,
                inputs={
                    "unis_estaca_sd": estaca,
                    "unis_col_fechadef": "params:bajas_calac.unis_col_fechadef",
                    "unis_col_fechatemp": "params:bajas_calac.unis_col_fechatemp",
                    "dict_duracion": "params:graduados_calac.dict_niveles_duracion",
                    "unis_calaca": calendario,
                    "fallback_weeks": "params:graduados_calac.graduation_fallback_weeks",
                    "left_on": "params:bajas_calac.merge_left_on",
                    "right_on": "params:bajas_calac.merge_right_on",
                    "group_key": "params:bajas_calac.unis_calaca_col_cohorte_inicial",
                    "sort_cols": "params:bajas_calac.unis_calaca_col_sort",
                },
                outputs=out_bajas,  # <-- Dinámico
                name="node_momento_baja",
            ),
            node(
                func=momento_grado,
                inputs={
                    "unis_estaca": estaca,
                    "unis_calaca": calendario,
                    "dict_duracion": "params:graduados_calac.dict_niveles_duracion",
                    "col_gi": "params:graduados_calac.graduation_col_gi",
                    "fallback_weeks": "params:graduados_calac.graduation_fallback_weeks",
                    "join_left": "params:graduados_calac.graduation_join_keys_left",
                    "join_right": "params:graduados_calac.graduation_join_keys_right",
                },
                outputs=out_graduados,  # <-- Dinámico
                name="node_momento_graduacion",
            ),
            node(
                func=momento_activos,
                inputs={
                    "unis_estaca": estaca,
                    "unis_calaca": calendario,
                    "dict_duracion": "params:graduados_calac.dict_niveles_duracion",
                    "col_di": "params:activos_calac.col_di",
                    "col_gi": "params:activos_calac.col_gi",
                    "fallback_weeks": "params:graduados_calac.graduation_fallback_weeks",
                    "join_left": "params:activos_calac.join_keys_left",
                    "join_right": "params:activos_calac.join_keys_right",
                    "group_key": "params:activos_calac.group_key",
                },
                outputs=out_activos,  # <-- Dinámico
                name="nodo_momento_activos",
            ),
            node(
                func=consolidar_estados_calac,
                inputs=[
                    out_bajas,      # <-- Conecta dinámicamente
                    out_graduados,  # <-- Conecta dinámicamente
                    out_activos,    # <-- Conecta dinámicamente
                    "params:orden_columnas_universo",
                ],
                outputs=out_estados,  # <-- Dinámico
                name="nodo_consolidar_estados_calac",
            ),
            node(
                func=generate_train_coxph_forecast,
                inputs=[
                    out_estados,  # <-- Conecta dinámicamente
                    "params:col_survival",
                ],
                outputs=out_survival,  # <-- Dinámico
                name="nodo_generate_train_coxph_forecast",
            ),
        ]
    )