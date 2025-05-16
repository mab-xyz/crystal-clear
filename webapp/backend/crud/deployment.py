from sqlmodel import Session
from models.deployment import Deployment, DeploymentCreate

def create_deployment(session: Session, deployment_data: DeploymentCreate) -> Deployment:
    deployment = Deployment(**deployment_data.model_dump())
    session.add(deployment)
    session.commit()
    session.refresh(deployment)
    return deployment


def get_deployment(session: Session, address: str) -> Deployment | None:
    return session.get(Deployment, address)
