from src.prediction.domain.models_prediction import  ModelMetrics, PredictionResult, PredictionInput
from abc import ABC,abstractmethod


class PredictionModelPort(ABC):
    """Classe permettant de mettre en place le contrat pour une prédiction"""
    @abstractmethod
    def predict_item(self,features:PredictionInput)->PredictionResult:
        pass



class EvaluateModelPort(ABC):
    "Classe relative à l'évaluation du modèle que l'on a."
    @abstractmethod
    def evaluate(self,test_sample:list[PredictionInput],target_output:list[PredictionResult])->ModelMetrics:
        pass