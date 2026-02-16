from src.prediction.domain.models_prediction import PredictionInput,PredictionResult,ModelMetrics, TOUTES_LES_REGIONS
from src.prediction.ports.predict import PredictionModelPort,EvaluateModelPort
from src.prediction.application.use_cases_prediction import PredictConsumptionUseCase,EvaluateModelPerformanceUseCase


# Création des instances correctes
VALID_TEMPERATURES={r:15.0 for r in TOUTES_LES_REGIONS}
VALID_WIND_SPEED={r:15.0 for r in TOUTES_LES_REGIONS}
VALID_HUMIDITY={r:15.0 for r in TOUTES_LES_REGIONS}

fake_input=PredictionInput(date="25/04/2013",hour=19,temp_regions=VALID_TEMPERATURES,wind_regions=VALID_WIND_SPEED,humidity_regions=VALID_HUMIDITY)
fake_input_2=PredictionInput(date="25/05/2013",hour=19,temp_regions=VALID_TEMPERATURES,wind_regions=VALID_WIND_SPEED,humidity_regions=VALID_HUMIDITY)
fake_result=PredictionResult(date="26/08/2017",hour=21,power=23.9)
fake_test_sample=[]
fake_test_sample_2=[]
fake_target_output=[]
fake_target_output_2=[]
for i in range(10):
    fake_test_sample.append(fake_input)
    fake_target_output.append(fake_result)
    fake_test_sample_2.append(fake_input)
    fake_target_output_2.append(fake_result)

fake_test_sample_2.append(fake_input)
fake_target_output_2.append(fake_result)


# Création des fakes adapters

class FakeAdapterPredictionModel(PredictionModelPort):
    """Fake adapter pour implémenter le port PredictionModel. On pourra ainsi faire appel au usecase PredictConsumptionUseCase"""
    
    def __init__(self):
        pass

    def predict_item(self,features:PredictionInput)->PredictionResult:
        return(PredictionResult(date="25/04/2013",hour=9,power=92.2))


class FakeAdapterEvaluationModel(EvaluateModelPort):
    def __init__(self):
        pass

    def evaluate(self,test_sample:list[PredictionInput],target_output:list[PredictionResult])->ModelMetrics:
        return(ModelMetrics(mae=1.0,rmse=2.0,mape=3.0))
    


def test_use_case_prediction_returns_good_type():
    fake_adapter_prediction=FakeAdapterPredictionModel()
    use_case_tested=PredictConsumptionUseCase(input=fake_input,method=fake_adapter_prediction)
    result=use_case_tested.execute_prediction_item()
    assert type(result) is PredictionResult

def test_use_case_prediction_delegates_method():
    fake_adapter_prediction=FakeAdapterPredictionModel()
    use_case_tested=PredictConsumptionUseCase(input=fake_input,method=fake_adapter_prediction)
    result=use_case_tested.execute_prediction_item()
    assert result.date=="25/04/2013"
    assert result.hour==9
    assert result.power==92.2
    

def test_use_case_prediction_delegation_not_depend_on_input():
    fake_adapter_prediction=FakeAdapterPredictionModel()
    use_case_tested=PredictConsumptionUseCase(input=fake_input_2,method=fake_adapter_prediction)
    result=use_case_tested.execute_prediction_item()
    assert result.date=="25/04/2013"
    assert result.hour==9
    assert result.power==92.2

def test_use_case_evaluation_returns_good_type():
    fake_adapter_evaluation=FakeAdapterEvaluationModel()
    use_case_tested=EvaluateModelPerformanceUseCase(fake_test_sample,fake_target_output,fake_adapter_evaluation)
    result=use_case_tested.evaluate_model()
    assert type(result) is ModelMetrics

def test_use_case_evaluation_delagates_method():
    fake_adapter_evaluation=FakeAdapterEvaluationModel()
    use_case_tested=EvaluateModelPerformanceUseCase(fake_test_sample,fake_target_output,fake_adapter_evaluation)
    result=use_case_tested.evaluate_model()
    assert result.mae==1.0
    assert result.rmse==2.0
    assert result.mape==3.0

def test_use_case_evaluation_does_not_depend_on_input():
    fake_adapter_evaluation=FakeAdapterEvaluationModel()
    use_case_tested=EvaluateModelPerformanceUseCase(fake_test_sample_2,fake_target_output,fake_adapter_evaluation)
    result=use_case_tested.evaluate_model()
    assert result.mae==1.0
    assert result.rmse==2.0
    assert result.mape==3.0