from src.prediction.domain.models_prediction import PredictionResult, ModelMetrics, TOUTES_LES_REGIONS, PredictionInput
import pytest

# Tests liés à PredictionResult

def test_prediction_result_date_valide():
    result=PredictionResult(date="25/04/2005",hour=18,power=64.7)
    assert result.date=="25/04/2005"

def test_prediction_result_hour_valide():
    result=PredictionResult(date="25/04/2005",hour=18,power=64.7)
    assert result.hour==18

def test_prediction_result_power_valide():
    result=PredictionResult(date="25/04/2005",hour=18,power=64.7)
    assert result.power==64.7

def test_type_date_incorrect():
    """Lever une erreur si la date n'est pas une string"""
    with pytest.raises(TypeError):
        PredictionResult(date=24382,hour=18,power=75.6)


def test_type_hour_incorrect():
    """Lever une erreur si l'heure est une string"""
    with pytest.raises(TypeError):
        PredictionResult(date="24/04/2016",hour="18",power=75.7)


def test_type_power_incorrect_string():
    """Lever une exception si power est sous forme de string"""
    with pytest.raises(TypeError):
        PredictionResult(date="24/04/2016",hour=18,power="75.7")


def test_date_vide():
    """Lever une exception si la date est vide"""
    with pytest.raises(ValueError):
        PredictionResult(date="",hour=18,power=75.7)


def test_date_composee_espaces():
    """Lever une exception si la date est uniquement composée d'espaces"""
    with pytest.raises(ValueError):
        PredictionResult(date=" ", hour=18, power=75.7)


def test_format_date_incorrect_AAAA_MM_DD():
    """Lever une exception si le format de la date est AAAA/MM/DD"""
    with pytest.raises(ValueError):
        PredictionResult(date="2015/04/28",hour=15,power=75.8)


def test_format_date_incorrect_MM_DD_AAAA():
    """Lever une exception si le format de la date est MM/DD/AAAA"""
    with pytest.raises(ValueError):
        PredictionResult(date="12/25/2016",hour=15,power=75.8)   


def test_format_date_incorrect_DD_MM_AA():
    """Lever une exception si le format de la date est DD/MM/AA"""
    with pytest.raises(ValueError):
        PredictionResult(date="28/04/25",hour=15,power=75.8)

     
def test_hour_negative():
    """Lever une exception si l'heure est négative"""
    with pytest.raises(ValueError):
        PredictionResult(date="25/04/2005",hour=-3,power=75.7)


def test_hour_trop_grande():
    """Lever une exception si l'heure est supérieure à 23"""
    with pytest.raises(ValueError):
        PredictionResult(date="25/04/2005",hour=24,power=75.7)


def test_power_negative():
    """Lever une exception si la production est trop faible"""
    with pytest.raises(ValueError):
        PredictionResult(date="25/04/2005",hour=23,power=-1)


def test_power_trop_grande():
    """Lever une exception si la production est trop importante"""
    with pytest.raises(ValueError):
        PredictionResult(date="25/04/2005",hour=23,power=170)


# Tests liés à ModelMetrics

def test_mae_valide():
    """Ce test sert à vérifier que le domaine retourne bien mae quand celui-ci est valide"""
    result=ModelMetrics(mae=23.4,rmse=68.8,mape=35.1)
    assert result.mae==23.4

def test_rmse_valide():
    """Ce test sert à vérifier que le domaine retourne bien rmse lorsque celui-ci est valide"""
    result=ModelMetrics(mae=23.4,rmse=68.8,mape=35.1)
    assert result.rmse==68.8

def test_mape_valide():
    """Ce test sert à vérifier que le domaine retourne bien mape quand celui-ci est valide"""
    result=ModelMetrics(mae=23.4,rmse=68.8,mape=35.1)
    assert result.mape==35.1

def test_type_mae_incorrect():
    """Lève une erreur si mae est une string"""
    with pytest.raises(TypeError):
        ModelMetrics(mae="22.8",rmse=28.4,mape=55.3)


def test_type_rmse_incorrect():
    """Lève une erreur si rmse est une string"""
    with pytest.raises(TypeError):
        ModelMetrics(mae=22.5,rmse="28.4",mape=55.2)


def test_type_mape_incorrect():
    """Lève une erreur si mape est une string"""
    with pytest.raises(TypeError):
        ModelMetrics(mae=22.7,rmse=28.4,mape="55.3")


def test_mae_negative():
    """Lève une erreur si mae est négative"""
    with pytest.raises(ValueError):
        ModelMetrics(mae=-3.5,rmse=28.4,mape=55.9)


def test_rmse_negative():
    """Lève une erreur si rmse est négative"""
    with pytest.raises(ValueError):
        ModelMetrics(mae=3.5,rmse=-38.2,mape=55.9)


def test_mape_negative():
    """Lève une erreur si mape est négative"""
    with pytest.raises(ValueError):
        ModelMetrics(mae=3.5,rmse=38.2,mape=-0.1)


# Tests associés à PredictionInput

"""Dans PredictionInput, je vais avoir besoin de quoi ?

    Qu'est ce qu'un input ?
    - Date : str formaté en DD/MM/AAAA
    - Heure : int | float entre [0-23]
    - Température : dictionnaire {chef_lieu(str):température(int|float)}
    - Wind_speed : dictionnaire {chef_lieu(str):wind_speed(int|float)}
    - Humidité : dictionnaire {chef_lieu(str):humidity(int|float)}


    Types d'erreurs que je dois lever : 

    TypeError : Sur les 5 paramètres
    ValueError :
        - Date au mauvais format
        - heure pas dans [0-23]
        - Température : 
            - Les noms des chefs lieux ne sont pas corrects
            - Les chefs lieux ne sont pas dans le bon ordre ?
            - Les températures sont incohérentes (-50 degrés ou 90 degrés)
        - Wind_speed :
            - Les noms des chefs lieux ne sont pas corrects
            - Les chefs lieux ne sont pas dans le bon ordre ?
            - Les vitesses sont incohérentes (négatives ou invraissemblables)
        - Humidité relative :
            - Les noms des chefs lieux ne sont pas corrects
            - Les chefs lieux ne sont pas dans le bon ordre ?
            - Les pourcentages sont incohérents (négatives ou supérieurs à 100%)

    """


VALID_TEMPERATURES={r:15.0 for r in TOUTES_LES_REGIONS}
VALID_WIND_SPEED={r:15.0 for r in TOUTES_LES_REGIONS}
VALID_HUMIDITY={r:15.0 for r in TOUTES_LES_REGIONS}


def test_prediction_input_date_valide():
    resultat=PredictionInput(date="24/07/2007",hour=17,temp_regions=VALID_TEMPERATURES,wind_regions=VALID_WIND_SPEED,humidity_regions=VALID_HUMIDITY)
    assert resultat.date=="24/07/2007"


def test_prediction_input_hour_valide():
    resultat=PredictionInput(date="24/07/2007",hour=17,temp_regions=VALID_TEMPERATURES,wind_regions=VALID_WIND_SPEED,humidity_regions=VALID_HUMIDITY)
    assert resultat.hour==17


def test_prediction_input_temp_valide():
    resultat=PredictionInput(date="24/07/2007",hour=17,temp_regions=VALID_TEMPERATURES,wind_regions=VALID_WIND_SPEED,humidity_regions=VALID_HUMIDITY)
    assert resultat.temp_regions==VALID_TEMPERATURES


def test_prediction_input_wind_valide():
    resultat=PredictionInput(date="24/07/2007",hour=17,temp_regions=VALID_TEMPERATURES,wind_regions=VALID_WIND_SPEED,humidity_regions=VALID_HUMIDITY)
    assert resultat.wind_regions==VALID_WIND_SPEED
    

def test_prediction_input_humidity_valide():
    resultat=PredictionInput(date="24/07/2007",hour=17,temp_regions=VALID_TEMPERATURES,wind_regions=VALID_WIND_SPEED,humidity_regions=VALID_HUMIDITY)
    assert resultat.humidity_regions==VALID_HUMIDITY


@pytest.mark.parametrize("valeur_date, erreur_attendue", [
    ("2015/04/15",ValueError),
    ("11/22/2016",ValueError),
    ("11/22/16",ValueError),
    ("vingt",ValueError),
    ("",ValueError),
    (" ",ValueError),
    (17834,TypeError)])
def test_prediction_input_date_invalide(valeur_date, erreur_attendue):
    with pytest.raises(erreur_attendue):
        PredictionInput(date=valeur_date,hour=17,temp_regions=VALID_TEMPERATURES,wind_regions=VALID_WIND_SPEED,humidity_regions=VALID_HUMIDITY)


@pytest.mark.parametrize("valeur_hour, erreur_attendue", [
    (-1,ValueError),
    (24,ValueError),
    ("vingt",TypeError)])
def test_prediction_input_hour_invalide(valeur_hour, erreur_attendue):
    with pytest.raises(erreur_attendue):
        PredictionInput(date="24/07/2007",hour=valeur_hour,temp_regions=VALID_TEMPERATURES,wind_regions=VALID_WIND_SPEED,humidity_regions=VALID_HUMIDITY)


@pytest.mark.parametrize("valeur_temperature, erreur_attendue", [
    (-50,ValueError),
    (80,ValueError),
    ("vingt",TypeError)])
@pytest.mark.parametrize("region",TOUTES_LES_REGIONS)
def test_prediction_input_dico_temp_invalide(valeur_temperature,erreur_attendue,region):
    mauvaises_temp={r:15.0 for r in TOUTES_LES_REGIONS}
    mauvaises_temp[region]=valeur_temperature
    with pytest.raises(erreur_attendue):
        PredictionInput(date="24/07/2007",hour=17,temp_regions=mauvaises_temp,wind_regions=VALID_WIND_SPEED,humidity_regions=VALID_HUMIDITY)


@pytest.mark.parametrize("valeur_wind, erreur_attendue", [
    (-1,ValueError),
    (250,ValueError),
    ("vingt",TypeError)])
@pytest.mark.parametrize("region",TOUTES_LES_REGIONS)
def test_prediction_input_dico_wind_invalide(valeur_wind,erreur_attendue,region):
    mauvais_wind={r:15.0 for r in TOUTES_LES_REGIONS}
    mauvais_wind[region]=valeur_wind
    with pytest.raises(erreur_attendue):
        PredictionInput(date="24/07/2007",hour=17,temp_regions=VALID_TEMPERATURES,wind_regions=mauvais_wind,humidity_regions=VALID_HUMIDITY)



@pytest.mark.parametrize("valeur_humidity, erreur_attendue", [
    (-1,ValueError),
    (101,ValueError),
    ("vingt",TypeError)])
@pytest.mark.parametrize("region",TOUTES_LES_REGIONS)
def test_prediction_input_dico_humidity_invalide(valeur_humidity,erreur_attendue,region):
    mauvaise_humidity={r:15.0 for r in TOUTES_LES_REGIONS}
    mauvaise_humidity[region]=valeur_humidity
    with pytest.raises(erreur_attendue):
        PredictionInput(date="24/07/2007",hour=17,temp_regions=VALID_TEMPERATURES,wind_regions=VALID_WIND_SPEED,humidity_regions=mauvaise_humidity)



