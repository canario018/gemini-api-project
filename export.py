from app.database.connection import Base, SessionLocal, engine
from app.opportunities.models import SurebetOpportunityModel, SurebetAlertModel
from app.opportunities.service import export_dashboard_json


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        count = export_dashboard_json(db, "data/opportunities/dashboard_opportunities.json")
    finally:
        db.close()
    print(f"Dataset do dashboard exportado: {count} oportunidades")


if __name__ == "__main__":
    main()
