"""
This is a boilerplate pipeline 'calac_activos_baj_grad'
generated using Kedro 1.2.0
"""


from kedro.pipeline import Node, Pipeline, node, pipeline
from .nodes import momento_baja,\
                   momento_grado,\
                   momento_activos,\
                   consolidar_estados_calac,\
                   generate_train_coxph_forecast


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [node(
            func=momento_baja,
            inputs={
                "unis_estaca_sd": "unis_estaca_sd",
                "unis_col_fechadef": "params:bajas_calac.unis_col_fechadef",
                "unis_col_fechatemp": "params:bajas_calac.unis_col_fechatemp",
                "dict_duracion": "params:graduados_calac.dict_niveles_duracion",
                "unis_calaca": "unis_calendario_extendido_uptoday",
                "fallback_weeks": "params:graduados_calac.graduation_fallback_weeks",
                "left_on": "params:bajas_calac.merge_left_on", # 'fecha_baja'
                "right_on": "params:bajas_calac.merge_right_on", # 'fecha_inicio'
                "group_key": "params:bajas_calac.unis_calaca_col_cohorte_inicial",
                "sort_cols": "params:bajas_calac.unis_calaca_col_sort",
            },
            outputs="unis_bajas_calendario_academico",
            name="node_momento_baja"
        ),
        node(
                func=momento_grado,
                inputs={
                    "unis_estaca": "unis_estaca_sd",
                    "unis_calaca": "unis_calendario_extendido_uptoday",
                    "dict_duracion": "params:graduados_calac.dict_niveles_duracion",
                    "col_gi": "params:graduados_calac.graduation_col_gi",
                    "fallback_weeks": "params:graduados_calac.graduation_fallback_weeks",
                    "join_left": "params:graduados_calac.graduation_join_keys_left",
                    "join_right": "params:graduados_calac.graduation_join_keys_right",
                },
                outputs="unis_graduados_calendario_academico",
                name="node_momento_graduacion"
            ),
        node(
                func=momento_activos,
                inputs={
                    "unis_estaca": "unis_estaca_sd",              # Dataset maestro
                    "unis_calaca": "unis_calendario_extendido_uptoday",   # Maestro calendario
                    "dict_duracion": "params:graduados_calac.dict_niveles_duracion", # Reutilizamos dict
                    "col_di": "params:activos_calac.col_di",            # 'di'
                    "col_gi": "params:activos_calac.col_gi",            # 'gi'
                    "fallback_weeks": "params:graduados_calac.graduation_fallback_weeks",
                    "join_left": "params:activos_calac.join_keys_left",  # 'fecha_activo'
                    "join_right": "params:activos_calac.join_keys_right",# 'fecha_inicio'
                    "group_key": "params:activos_calac.group_key",       # 'cohorte_inicial'
                },
                outputs="unis_activos_calendario",
                name="nodo_momento_activos",
            ),
            node(
            func=consolidar_estados_calac,
            inputs=[
                "unis_bajas_calendario_academico",
                "unis_graduados_calendario_academico",
                "unis_activos_calendario",
                "params:orden_columnas_universo",
            ],
            outputs="unis_estados_calac",
            name="nodo_consolidar_estados_calac"
        ),
        node(
            func=generate_train_coxph_forecast,
            inputs=[
                "unis_estados_calac",
                "params:col_survival",
            ],
            outputs="unis_estados_calac_survival",
            name="nodo_generate_train_coxph_forecast"
        ),
    ]
    )
