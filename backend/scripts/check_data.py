import sys
sys.path.insert(0, ".")

from src.electricity.adapters.persistence.sqlalchemy_repository import SQLAlchemyConsumptionRepository

repo = SQLAlchemyConsumptionRepository()
records = repo.get_by_date("01/01/2012")

print(f"Nombre d'enregistrements pour le 01/01/2012 : {len(records)}")
for r in records[:48]:
    print(f"  {r.date} {r.hour}h : {r.power:.2f} GW")