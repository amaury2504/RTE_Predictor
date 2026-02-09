import pytest
from src.electricity.domain.models import ConsumptionRecord

# Cas valide :

def test_creation_ConsumptionRecord_valide():
    """Objectif du test : 
    Montrer que quand on indique une consommation composée de la date-heure-puissance(GW), la consommation est considérée comme correcte.
    """
    instance_consumption=ConsumptionRecord(date="23/01/2026",hour=14,power=55.3)
    assert instance_consumption.date=="23/01/2026"
    assert instance_consumption.hour==14
    assert instance_consumption.power==55.3

# Date :

def test_creation_ConsumptionRecord_invalide_date_vide():
    """Lever une erreur si la date est vide
    """
    with pytest.raises(ValueError):
        ConsumptionRecord(date="",hour=14,power=55.3)

def test_creation_ConsumptionRecord_invalide_date_espaces():
    """Lever une erreur si la date est uniquement composée d'espaces
    """
    with pytest.raises(ValueError):
        ConsumptionRecord(date=" ",hour=20,power=55.3)

def test_creation_ConsumptionRecord_invalide_separateur_date():
    """Lever une erreur si la date n'a pas les bons séparateurs
    """
    with pytest.raises(ValueError):
        ConsumptionRecord(date="25-03-2025",hour=20,power=55.3)

def test_creation_ConsumptionRecord_invalide_format_date():
    """Lever une erreur si le format de la date n'est pas JJ/MM/AAAA
    """
    with pytest.raises(ValueError):
        ConsumptionRecord(date="2025/03/08",hour=20,power=55.3)

def test_creation_ConsumptionRecord_invalide_date_jour_trop_grand():
    """Lever une erreur si le jour est absurde (supérieur à 31)
    """
    with pytest.raises(ValueError):
        ConsumptionRecord(date="45/03/2025",hour=20,power=55.3)

def test_creation_ConsumptionRecord_invalide_date_jour_nul():
    """Lever une erreur si le jour est égal à 0.
    """
    with pytest.raises(ValueError):
        ConsumptionRecord(date="00/03/2025",hour=20,power=55.3)

def test_creation_ConsumptionRecord_invalide_date_mois_absurde():
    """Lever une erreur si le mois est absurde (supérieur à 12)
    """
    with pytest.raises(ValueError):
        ConsumptionRecord(date="20/13/2025",hour=20,power=55.3)

def test_creation_ConsumptionRecord_invalide_date_mois_nul():
    """Lever une erreur si le mois est absurde (égal à 0)
    """
    with pytest.raises(ValueError):
        ConsumptionRecord(date="20/00/2025",hour=20,power=55.3)

def test_creation_ConsumptionRecord_invalide_date_annee_future():
    """Lever une erreur si la valeur de l'année est plus grande que l'année en cours + 1
    """
    with pytest.raises(ValueError):
        ConsumptionRecord(date="20/12/2040",hour=20,power=55.3)

# Heures :

def test_creation_ConsumptionRecord_invalide_heure_negative():
    """Lever une erreur si la valeur de l'heure est négative
    """
    with pytest.raises(ValueError):
        ConsumptionRecord(date="25/03/2025",hour=-10,power=55.3)

def test_creation_ConsumptionRecord_invalide_heure_vide():
    """Lever une erreur si l'heure est invalide (supérieure à 24)
    """
    with pytest.raises(ValueError):
        ConsumptionRecord(date="23/01/2026",hour=25,power=55.3)

def test_creation_ConsumptionRecord_invalide_heure_type():
    """Lever une erreur si le type de l'heure est une string
    """
    with pytest.raises(TypeError):
        ConsumptionRecord(date="25/03/2025",hour="20",power=55.3)

# Puissance :

def test_creation_ConsumptionRecord_invalide_puissance_negative():
    """Lever une erreur si la puissance est négative
    """
    with pytest.raises(ValueError):
        ConsumptionRecord(date="23/01/2026",hour=20,power=-8)

def test_creation_ConsumptionRecord_invalide_puissance_absurde():
    """Lever une erreur si la puissance est supérieure au parc_francais
    """
    with pytest.raises(ValueError):
        ConsumptionRecord(date="23/01/2026",hour=20,power=171)

def test_creation_ConsumptionRecord_invalide_type_puissance():
    """Lever une erreur si la puissance est une string
    """
    with pytest.raises(TypeError):
        ConsumptionRecord(date="23/01/2026",hour=20,power="55.3")