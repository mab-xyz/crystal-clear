from sqlmodel import Session, select
from models.label import Label, LabelCreate, LabelUpdate, AddressList
from datetime import datetime
from typing import List, Dict

def create_label(session: Session, label_data: LabelCreate) -> Label:
    label = Label(**label_data.model_dump())
    session.add(label)
    session.commit()
    session.refresh(label)
    return label


def get_label(session: Session, address: str) -> Label | None:
    return session.get(Label, address)

def get_all_labels(session: Session) -> Dict[str, str]:
    result = session.exec(select(Label)).all()
    return {row.address: row.label for row in result}

def update_label(session: Session, address: str, label_data: LabelUpdate) -> Label | None:
    label = session.get(Label, address)
    if not label:
        return None
    label.label = label_data.label
    label.last_updated = datetime.now()
    session.add(label)
    session.commit()
    session.refresh(label)
    return label

def get_labels(session: Session, addresses: AddressList) -> List[Label]:
    stmt = select(Label).where(Label.address.in_(addresses.addresses))
    result = session.exec(stmt).all()
    return {row.address: row.label for row in result}