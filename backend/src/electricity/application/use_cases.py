from electricity.ports.repository import ConsumptionRepository
from electricity.domain.models import ConsumptionRecord

class StoreConsumption():
    """Classe qui permet de créer le use case enregistrant le record dans un repository"""

    def __init__(self,repository:ConsumptionRepository):
        self.repository=repository

    def execute(self,record:ConsumptionRecord):
        self.repository.save_record(record)

    
class GetConsumptionByDate():
    """Classe qui permet de recupérer les enregistrements de consommation d'une même date
    """

    def __init__(self,repository:ConsumptionRepository):
        self.repository=repository

    def get_extraction_by_date(self,date:str)->list[ConsumptionRecord]:
        resultat=self.repository.get_by_date(date)
        return(resultat)


class GetConsumptionByRange():
    """Classe qui permet de récupérer les enregistrements de consommation entre deux dates (date de fin incluse)"""

    def __init__(self,repository:ConsumptionRepository):
        self.repository=repository

    def get_extraction_by_range(self,date_start:str,date_end:str):
        resultat=self.repository.get_by_range(date_start,date_end)
        return(resultat)