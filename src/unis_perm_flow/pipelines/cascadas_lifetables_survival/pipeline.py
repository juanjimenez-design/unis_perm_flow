from kedro.pipeline import Pipeline, node, pipeline
from .nodes import crear_cascada_supervivencia,\
                    crear_cascada_supervivencia_mensual,\
                     calcular_km_y_eti_dinamico

def create_pipeline(**kwargs) -> Pipeline:
    # 1. Definimos el pipeline "maestro" de cálculo actuarial que será reutilizado
    calculo_base = pipeline([
        node(
            func=calcular_km_y_eti_dinamico,
            inputs={
                "df": "cascadas_semanal_podada_censuras",
                "unidades_tiempo": "params:unidades_tiempo" ,# Nombre relativo al namespace
                "group_cols": "params:group_columnas_agrupacion" # Nombre relativo al namespace
            },
            outputs="unis_tabla_vida_semanal", # Nombre relativo al namespace
            name="nodo_calculo_km_eti",
        )
    ])

    calculo_base_mensual = pipeline([
        node(
            func=calcular_km_y_eti_dinamico,
            inputs={
                "df": "cascadas_mensual_podada_censuras",
                "unidades_tiempo": "params:unidades_tiempo" ,# Nombre relativo al namespace
                "group_cols": "params:group_columnas_agrupacion" # Nombre relativo al namespace
            },
            outputs="unis_tabla_vida_mensual", # Nombre relativo al namespace
            name="nodo_calculo_km_eti",
        )
    ])

    return Pipeline([
        # --- NODO DE INTEGRACIÓN (Se ejecuta una sola vez) ---
        node(
            func=crear_cascada_supervivencia,
            inputs={
                "unis_estados_calac": "unis_estados_calac",
                "unis_calendario_extendido_uptoday": "unis_calendario_extendido_uptoday",
                "unis_bajas_calendario_academico": "unis_bajas_calendario_academico",
                "unis_graduados_calendario_academico": "unis_graduados_calendario_academico",
                "dict_niveles_duracion": "params:survival.dict_niveles_duracion",
                "params": "params:survival"
            },
            outputs="cascadas_semanal_podada_censuras",
            name="nodo_crear_cascada_supervivencia",
        ),
        node(
            func=crear_cascada_supervivencia_mensual,
            inputs={
                "df": "cascadas_semanal_podada_censuras",
                "group_columns": "params:survival_mensual.group_columnas_agrupacion"
            },
            outputs="cascadas_mensual_podada_censuras",
            name="nodo_crear_cascada_supervivencia_mensual",
        ),

        # --- INSTANCIAS CON NAMESPACE ---
        # Mapeamos el input global "cascadas_semanal_podada_censuras" a cada namespace
        
        # Semanal --------------------------------------------------------------------
        pipeline(
            calculo_base,
            namespace="lifetables_programa",
            inputs={"cascadas_semanal_podada_censuras": "cascadas_semanal_podada_censuras"}
        ),
        
        pipeline(
            calculo_base,
            namespace="lifetables_nivel",
            inputs={"cascadas_semanal_podada_censuras": "cascadas_semanal_podada_censuras"}
        ),
        
        
        pipeline(
            calculo_base,
            namespace="lifetables_cohorte",
            inputs={"cascadas_semanal_podada_censuras": "cascadas_semanal_podada_censuras"}
        ),

        # Mensual --------------------------------------------------------------------
        pipeline(
            calculo_base_mensual,
            namespace="lifetables_mensuales_programa",
            inputs={"cascadas_mensual_podada_censuras": "cascadas_mensual_podada_censuras"}
        ),
        
        pipeline(
            calculo_base_mensual,
            namespace="lifetables_mensuales_nivel",
            inputs={"cascadas_mensual_podada_censuras": "cascadas_mensual_podada_censuras"}
        ),
        
        
        pipeline(
            calculo_base_mensual,
            namespace="lifetables_mensuales_cohorte",
            inputs={"cascadas_mensual_podada_censuras": "cascadas_mensual_podada_censuras"}
        ),
    ])