"""
This is a boilerplate pipeline 'survival_model'
generated using Kedro 1.2.0
"""

from kedro.pipeline import Pipeline, node, pipeline
from .nodes import preprocess_survival_data, train_survival_model

def create_pipeline(**kwargs) -> Pipeline:
    return pipeline([
        node(
            func=preprocess_survival_data,
            inputs=["unis_estados_calac_survival_presupuesto", "params:survival_model_presupuesto"],
            outputs="df_cox_preparado_presupuesto",
            name="node_preprocess_survival_data_presupuesto",
        ),
        node(
            func=train_survival_model,
            inputs=["df_cox_preparado", "params:survival_model_presupuesto"],
            outputs="modelo_cox_desercion_presupuesto",
            name="node_train_survival_model_presupuesto",
        ),
    ])
