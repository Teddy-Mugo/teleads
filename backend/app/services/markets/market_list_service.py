from sqlalchemy.orm import Session
from app.models.models import MarketList, TelegramGroup


def create_market_list(
    *,
    db: Session,
    customer_id,
    name: str,
):
    market_list = MarketList(
        customer_id=customer_id,
        name=name,
    )
    db.add(market_list)
    db.commit()
    db.refresh(market_list)
    return market_list


def add_group_to_market_list(
    *,
    db: Session,
    market_list: MarketList,
    group: TelegramGroup,
):
    if group not in market_list.groups:
        market_list.groups.append(group)
        db.commit()


def remove_group_from_market_list(
    *,
    db: Session,
    market_list: MarketList,
    group: TelegramGroup,
):
    if group in market_list.groups:
        market_list.groups.remove(group)
        db.commit()
