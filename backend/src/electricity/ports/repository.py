from abc import ABC,abstractmethod
from electricity.domain.models import ConsumptionRecord


class ConsumptionRepository(ABC):
    @abstractmethod
    def save_record(self,record:ConsumptionRecord)->None:
        """Contrat pour stocker les enregistrements de consommation
        """
        pass

    @abstractmethod
    def get_by_date(self,date:str)->list[ConsumptionRecord]:
        """Récupérer les enregistrements d'une date
        """
        pass

    @abstractmethod
    def get_by_range(self,date_start:str,date_end:str)->list[ConsumptionRecord]:
        """Récupérer les enregistrements entre deux dates"""
        pass