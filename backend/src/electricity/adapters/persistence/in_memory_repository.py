from electricity.application.use_cases import ConsumptionRepository
from electricity.domain.models import ConsumptionRecord


class InMemoryConsumptionRepository(ConsumptionRepository):
    """C'est une simulation de l'implémentation de mon port ConsumptionRepository"""
    def __init__(self):
        self.records=[] # Initialisation de la liste
    
    def save_record(self,record:ConsumptionRecord):
        self.records.append(record)

    def get_by_date(self,date:str):
        return( [r for r in self.records if r.date==date])

    def get_by_range(self,date_start:str,date_end:str):
        return([r for r in self.records if r.date>=date_start and r.date<= date_end])
    