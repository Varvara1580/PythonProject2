from sqlalchemy.orm import Session
from sqlalchemy import select
from Models import Transaction, Category

def create_category(title: str, type: str, user_id: int, db: Session):
    t = Category(title = title, type = type, user_id = user_id)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t

def get_categories(db: Session):
    c = list(db.scalars(select(Category)).all())
    c.sort(key = lambda x: x.title)
    return c

def create_transaction(title: str, cost: int, category_id: int, user_id: int, db: Session):
    t = Transaction(title = title, cost = cost, category_id = category_id, user_id = user_id)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t

def get_user_transaction(user_id: int, db: Session):
    return list(db.scalars(select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.date.desc())))

def get_user_transaction_1(user_id: int, db: Session):
    return select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.date.desc())


def calculate_statistic(t: list[Transaction]):
    income = 0
    expense = 0
    for i in t:
        if i.category.type == 'income':
            income += i.cost
        else:
            expense += i.cost
    return {'income': income, 'expense': expense, 'balance': income - expense}