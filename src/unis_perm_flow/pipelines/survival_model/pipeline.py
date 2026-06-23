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
            inputs=["unis_estados_calac_survival", "params:survival_model"],
            outputs="df_cox_preparado",
            name="node_preprocess_survival_data",
        ),
        node(
            func=train_survival_model,
            inputs=["df_cox_preparado", "params:survival_model"],
            outputs="modelo_cox_desercion",
            name="node_train_survival_model",
        ),
    ])
