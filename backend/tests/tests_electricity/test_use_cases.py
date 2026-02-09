from src.electricity.ports.repository import ConsumptionRepository
from src.electricity.domain.models import ConsumptionRecord
from src.electricity.application.use_cases import StoreConsumption, GetConsumptionByDate, GetConsumptionByRange

class FakeConsumptionRepository(ConsumptionRepository):
    """C'est une simulation de l'implémentation de mon port ConsumptionRepository"""
    def __init__(self):
        self.records=[] # Initialisation de la liste
    
    def save_record(self,record:ConsumptionRecord):
        self.records.append(record)

    def get_by_date(self,date:str):
        return( [r for r in self.records if r.date==date])

    def get_by_range(self,date_start:str,date_end:str):
        return([r for r in self.records if r.date>=date_start and r.date<= date_end])
    


def test_store_consumption_saves_record():
    """Le use case doit sauvegarder un record via le repository"""
    
    # Arrange : 
    fake_repo=FakeConsumptionRepository()
    record=ConsumptionRecord(date="23/01/2025",hour=14,power=45.3)
    use_case=StoreConsumption(fake_repo)

    # Act : 
    use_case.execute(record)

    # Assert : Vérifier que le record a été sauvegardé
    assert len(fake_repo.records)==1
    assert fake_repo.records[0].date=="23/01/2025"
    assert fake_repo.records[0].hour==14
    assert fake_repo.records[0].power==45.3


def test_get_consumption_record_by_date():
    """Le use case doit permettre de récupérer une information à l'intérieur d'un repository"""

    # Arrange : Création d'un repository fake avec des données à l'intérieur
    fake_repo=FakeConsumptionRepository()
    record=ConsumptionRecord(date="23/01/2025",hour=14,power=45.3)
    record2=ConsumptionRecord(date="23/01/2025",hour=14,power=45.3)
    record3=ConsumptionRecord(date="24/01/2025",hour=14,power=45.3)
    
    store_use_case=StoreConsumption(fake_repo)
    store_use_case.execute(record)
    store_use_case.execute(record2)
    store_use_case.execute(record3)

    use_case=GetConsumptionByDate(fake_repo)
    

    # Act : Executer le process
    resultat=use_case.get_extraction_by_date(date="23/01/2025")
    
    # Assert : Vérifier si tout s'est bien passé

    assert len(resultat)==2
    assert record in resultat
    assert record2 in resultat
    assert record3 not in resultat


def test_get_consumption_records_by_range():
    """Le test sert à simuler l'extraction de plusieurs enregistrements de consommation entre 2 dates"""
    
    # Arrange
    fake_repo=FakeConsumptionRepository()
    record=ConsumptionRecord(date="25/01/2020",hour=18,power=55.7)
    record1=ConsumptionRecord(date="26/01/2020",hour=19,power=55.7)
    record2=ConsumptionRecord(date="27/01/2020",hour=2,power=55.7)
    record3=ConsumptionRecord(date="28/01/2020",hour=23,power=55.7)
    record4=ConsumptionRecord(date="25/01/2021",hour=18,power=55.7)
    
    store_use_case=StoreConsumption(fake_repo)
    store_use_case.execute(record)
    store_use_case.execute(record1)
    store_use_case.execute(record2)
    store_use_case.execute(record3)
    store_use_case.execute(record4)


    # Get : Test du use_case get_by_range

    use_case=GetConsumptionByRange(fake_repo)
    resultat=use_case.get_extraction_by_range(date_start="26/01/2020",date_end="27/01/2020")

    # Assert :

    assert len(resultat)==2
    assert record not in resultat
    assert record1 in resultat
    assert record2 in resultat
    assert record3 not in resultat
    assert record4 not in resultat
    