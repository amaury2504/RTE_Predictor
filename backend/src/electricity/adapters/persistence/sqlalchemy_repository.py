from src.electricity.ports.repository import ConsumptionRepository
from src.electricity.domain.models import ConsumptionRecord
from src.electricity.adapters.persistence.sqlalchemy_models import ConsumptionRecordDB, SessionLocal

class SQLAlchemyConsumptionRepository(ConsumptionRepository):
    def save_record(self,record:ConsumptionRecord)->None:
        
        # Conversion de ConsumptionRecord ver
        consumption_record_db=ConsumptionRecordDB(date=record.date,hour=record.hour,power=record.power)
        # Ouverture de la session
        session = SessionLocal()

        #Ajout de notre objet dans la DB
        session.add(consumption_record_db)

        #Commit
        session.commit()

        #Fermeture de session
        session.close()


    def get_by_date(self, date_query:str)->list[ConsumptionRecord]:
        # Ouverture de la session
        session=SessionLocal()

        # Demande de filtrage
        tableau_extrait=session.query(ConsumptionRecordDB).filter(ConsumptionRecordDB.date==date_query)
        
        # Conversion des items ConsumptionRecordDB en ConsumptionRecord
        consumption_record_by_date=[]
        for record_db in tableau_extrait:

            record=ConsumptionRecord(record_db.date,record_db.hour,record_db.power)
            consumption_record_by_date.append(record)

        #Fermeture de session
        session.close()
        return(consumption_record_by_date)

    def get_by_range(self,date_start_db:str,date_end_db:str)->list[ConsumptionRecord]:
        
        # Ouverture de la session
        session=SessionLocal()

        # Demande de filtrage
        tableau_extrait=session.query(ConsumptionRecordDB).filter(ConsumptionRecordDB.date>=date_start_db).filter(ConsumptionRecordDB.date<=date_end_db)
        
        # Conversion des items ConsumptionRecordDB en ConsumptionRecord
        consumption_record_by_range=[]
        for record_db in tableau_extrait:
            record=ConsumptionRecord(record_db.date,record_db.hour,record_db.power)
            consumption_record_by_range.append(record)

        # Fermeture de session    
        session.close()
        return(consumption_record_by_range)




        