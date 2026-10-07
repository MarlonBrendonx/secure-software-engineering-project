from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from nbb.api.deps import Current, error, get_current, require
from nbb.core.permissions import P
from nbb.db import get_db
from nbb.models import Setting
from nbb.services import settings as svc

router = APIRouter(prefix="/settings", tags=["configuracoes"])


class SettingOut(BaseModel):
    key: str
    value: Any
    description: str
    updated_at: datetime


@router.get("", response_model=list[SettingOut], summary="Parâmetros do sistema")
def list_settings(current: Current = Depends(get_current), db: Session = Depends(get_db)):
    return [SettingOut.model_validate(s, from_attributes=True) for s in db.scalars(select(Setting).order_by(Setting.key))]


@router.put("/{key}", response_model=SettingOut, summary="Altera um parâmetro")
def update_setting(key: str, value: Any = Body(embed=True),
                   current: Current = Depends(require(P.SETTINGS_MANAGE)), db: Session = Depends(get_db)):
    try:
        row = svc.set_value(db, key, value, current.user.id)
    except KeyError:
        raise error(404, "not_found", "Parâmetro desconhecido.") from None
    except ValueError as exc:
        raise error(422, "invalid_value", str(exc)) from None
    db.commit()
    return SettingOut.model_validate(row, from_attributes=True)
