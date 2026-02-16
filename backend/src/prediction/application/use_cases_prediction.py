from src.prediction.domain.models_prediction import PredictionInput, PredictionResult, ModelMetrics
from src.prediction.ports.predict import PredictionModelPort,EvaluateModelPort

class PredictConsumptionUseCase():
    """Ce use case sert à orchestrer les étapes pour passer d'un Prediction Input à un PredictionResult
    
    Args : 
    - Input : PredictionInput
    
    Returns : 
    - Output : PredictionResult
    """

    def __init__(self,input,method:PredictionModelPort):
        self.input=input
        methode_utilisee=method
        self.methode=methode_utilisee

    def execute_prediction_item(self)->PredictionResult:
        # Fonction qui orchestre la prediction
        resultat=self.methode.predict_item(self.input)
        return(resultat)
    
class EvaluateModelPerformanceUseCase():
    """Classe qui permet d'évaluer le modèle que l'on utilise. 
    
    Args : 
        - test_sample : (échantillon test de features). Type : List(PredictionInput)
        - target_output : (Sortie que l'on doit avoir). Type : List(PredictionResult)

    Returns:
        mae,rmse,mape: Métriques du modèle. Type : ModèleMetrics
    """

    def __init__(self,test_sample : list[PredictionInput],target_output:list[PredictionResult],method:EvaluateModelPort):
        self.test_sample=test_sample
        self.target_output=target_output
        self.methode=method

    def evaluate_model(self)->ModelMetrics:
        metriques=self.methode.evaluate(self.test_sample,self.target_output)
        return(metriques)
