from app.core.db import engine, Base
from app.models.models import SubscriptionPlan, MarketList, Customer, TelegramAccount, Campaign

def main():
    print("ENGINE URL:", engine.url)
    print("CREATING TABLES...")
    Base.metadata.create_all(bind=engine)
    print("DONE")

if __name__ == "__main__":
    main()

