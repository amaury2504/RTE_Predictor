from src.prediction.domain.models_prediction import PredictionInput, ModelMetrics, PredictionResult
from src.prediction.ports.predict import PredictionModelPort, EvaluateModelPort
import torch
import holidays
import pandas as pd
import torch.nn as nn
import numpy as np

class ConsumptionModel(nn.Module):
    def __init__(self, input_size):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, 256),
            nn.LeakyReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.LeakyReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.LeakyReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, 32),
            nn.LeakyReLU(),
            nn.Linear(32, 1)
        )

    def forward(self, x):
        return self.network(x)


class PredictWithPytorch(PredictionModelPort):
    """Comment implémenter concrètement la prédiction grâce à notre réseau de neurones (En utilisant PyTorch)."""

    def __init__(self,model,scaler_X,scaler_Y):
        self.model=model
        self.scaler_X=scaler_X
        self.scaler_Y=scaler_Y
        
        pass

    def predict_item(self,input:PredictionInput)->PredictionResult:

        datetime=pd.to_datetime(input.date,format="%d/%m/%Y")
        fr_holidays=holidays.France()

    #2. Construire un dictionnaire avec toutes les features

        features={}

    # Heure
        features["hour"]=input.hour

    # Températures + Températures^2

        for region, temp in input.temp_regions.items():
            features[f"temperature_{region}"]=temp
            features[f"temperature_{region}_squared"]=temp**2

    # Vents

        for region, wind_speed in input.wind_regions.items():
            features[f"wind_speed_{region}"]=wind_speed

    # Humidity

        for region,humidity in input.humidity_regions.items():
            features[f"humidity_{region}"]=humidity

    # Features temporelles 

        features["month"]=datetime.month
        features["dayofweek"]=datetime.dayofweek
        features["is_holiday"]=1 if datetime in fr_holidays else 0

        date_originale=input.date
        hour_originale=input.hour

        df = pd.DataFrame([features])
        df = df[self.scaler_X.feature_names_in_]
        input=df

        # Normalisation des features

        input_normalized=self.scaler_X.transform(input)
        
        # Appel de mon modèle
        self.model.eval()
        with torch.no_grad():
            input_tensor=torch.FloatTensor(input_normalized)
            prediction_normalized=self.model(input_tensor).numpy()

        # Dénormalisation de la prédiction

        prediction=self.scaler_Y.inverse_transform(prediction_normalized)
        return(PredictionResult(date=date_originale,hour=hour_originale,power=float(prediction[0][0])))
    

class EvaluateWithPytorch(EvaluateModelPort):
    """Implémenter l'évaluation de mon modèle avec Pytorch"""
    def __init__(self,model,scaler_X,scaler_Y):
        self.model=model
        self.scaler_X=scaler_X
        self.scaler_Y=scaler_Y
        pass


    def evaluate(self,test_sample:list[PredictionInput],target_output:list[PredictionResult])->ModelMetrics:


        # Transformation du test_sample

        test_sample_normalized=self.scaler_X.transform(test_sample)
        
        self.model.eval()
        with torch.no_grad():

            test_sample_tensor=torch.FloatTensor(test_sample_normalized)
            result_predicted=self.model(test_sample_tensor).numpy()

            # Reconversion des prédiction en données réelles 

        real_output=self.scaler_Y.inverse_transform(result_predicted)

        stockage_values_for_mae=[]
        stockage_values_for_rmse=[]
        stockage_values_for_mape=[]
        for i in range(len(target_output)):
            target=target_output[i].power
            prediction=real_output[i]
            stockage_values_for_mae.append(abs(target-prediction))
            stockage_values_for_rmse.append((target-prediction)**2)
            stockage_values_for_mape.append(abs(target-prediction)/abs(target)*100)
        mae=np.mean(stockage_values_for_mae)
        rmse=np.sqrt(np.mean(stockage_values_for_rmse))
        mape=np.mean(stockage_values_for_mape)

        return(ModelMetrics(mae,rmse,mape))
            



