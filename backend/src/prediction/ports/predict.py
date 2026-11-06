from src.prediction.domain.models_prediction import PredictionInput, ModelMetrics, PredictionResult
from abc import ABC,abstractmethod


class PredictionModelPort(ABC):
    """Classe permettant de mettre en place le contrat pour une prédiction"""
    @abstractmethod
    def predict_item(self,features:PredictionInput)->PredictionResult:
        pass

    def predict_items(self,inputs:list[PredictionInput])->list[PredictionResult]:
        """Prédit un lot. Par défaut, une prédiction après l'autre ; un modèle peut regrouper le calcul."""
        return [self.predict_item(i) for i in inputs]



class EvaluateModelPort(ABC):
    "Classe relative à l'évaluation du modèle que l'on a."
    @abstractmethod
    def evaluate(self,test_sample:list[PredictionInput],target_output:list[PredictionResult])->ModelMetrics:
        pass
