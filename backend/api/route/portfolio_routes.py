# backend/api/routes/portfolio_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from database import get_db, Portfolio, User
from api.auth import get_current_user

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

class PortfolioItem(BaseModel):
    ticker:       str
    company_name: str
    shares:       Optional[float] = 0
    buy_price:    Optional[float] = 0

# 新增股票
@router.post("/")
def add_stock(
    item: PortfolioItem,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user)
):
    # 同一支股票不重複新增
    existing = db.query(Portfolio).filter(
        Portfolio.user_id == user.id,
        Portfolio.ticker  == item.ticker
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="股票已在倉庫中")

    stock = Portfolio(
        user_id      = user.id,
        ticker       = item.ticker,
        company_name = item.company_name,
        shares       = item.shares,
        buy_price    = item.buy_price,
    )
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return {"message": "新增成功", "ticker": item.ticker}

# 取得所有持股
@router.get("/")
def get_portfolio(
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user)
):
    stocks = db.query(Portfolio).filter(Portfolio.user_id == user.id).all()
    return [
        {
            "id":           s.id,
            "ticker":       s.ticker,
            "company_name": s.company_name,
            "shares":       s.shares,
            "buy_price":    s.buy_price,
            "added_at":     str(s.added_at),
        }
        for s in stocks
    ]

# 刪除股票
@router.delete("/{portfolio_id}")
def delete_stock(
    portfolio_id: int,
    db:           Session = Depends(get_db),
    user:         User    = Depends(get_current_user)
):
    stock = db.query(Portfolio).filter(
        Portfolio.id      == portfolio_id,
        Portfolio.user_id == user.id
    ).first()
    if not stock:
        raise HTTPException(status_code=404, detail="找不到該股票")
    db.delete(stock)
    db.commit()
    return {"message": "刪除成功"}