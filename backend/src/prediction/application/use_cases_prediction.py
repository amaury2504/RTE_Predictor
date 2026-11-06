from src.prediction.domain.models_prediction import PredictionInput, PredictionResult, ModelMetrics
from src.prediction.ports.predict import PredictionModelPort,EvaluateModelPort
from src.prediction.domain.kpi import compute_kpis, KpiReport

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
    
class PredictBatchUseCase():
    """Orchestre la prédiction d'un lot d'entrées avec la méthode choisie (un seul calcul groupé si le modèle le permet).

    Args :
    - inputs : list[PredictionInput]

    Returns :
    - list[PredictionResult], dans le même ordre
    """

    def __init__(self,inputs:list[PredictionInput],method:PredictionModelPort):
        self.inputs=inputs
        self.methode=method

    def execute(self)->list[PredictionResult]:
        return self.methode.predict_items(self.inputs)


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


class ComputeKpisUseCase():
    """Calcule le rapport complet de KPI à partir de séries (prédit, réel) horodatées.

    Args:
        timestamps : horodatages locaux, un par point (ex. "2026-05-27T14:00")
        predicted : puissances prédites (GW)
        actual : puissances réelles (GW)

    Returns:
        KpiReport
    """

    def __init__(self,timestamps:list[str],predicted:list[float],actual:list[float]):
        self.timestamps=timestamps
        self.predicted=predicted
        self.actual=actual

    def execute(self)->KpiReport:
        return compute_kpis(self.timestamps,self.predicted,self.actual)
