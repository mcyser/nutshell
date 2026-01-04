import os
import time
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from loguru import logger

from ..core.settings import settings
from ..mint.startup import ledger
from ..core.base import MintQuoteState

router = APIRouter()

class SettleQuoteRequest(BaseModel):
    quote_id: str

async def log_audit(action: str, details: dict):
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    payload = {
        "action": action,
        "details": details,
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # POST to audit_logs table
            await client.post(f"{url}/rest/v1/audit_logs", json=payload, headers=headers)
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")

@router.post("/v1/admin/settle_quote", tags=["Admin"])
async def admin_settle_quote(
    payload: SettleQuoteRequest,
    x_admin_key: str = Header(..., alias="X-Admin-Key")
):
    admin_secret = os.getenv("MINT_ADMIN_KEY", settings.mint_private_key)
    if x_admin_key != admin_secret:
        await log_audit("settle_quote_unauthorized", {"quote_id": payload.quote_id})
        raise HTTPException(status_code=403, detail="Unauthorized")

    logger.info(f"Admin settling quote {payload.quote_id}")
    
    quote = await ledger.crud.get_mint_quote(quote_id=payload.quote_id, db=ledger.db)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
        
    if quote.state == MintQuoteState.paid:
         return {"status": "already_paid", "quote": quote.to_dict()}

    quote.state = MintQuoteState.paid
    quote.paid_time = int(time.time())
    
    await ledger.crud.update_mint_quote(quote=quote, db=ledger.db)
    
    await log_audit("settle_quote_success", {
        "quote_id": payload.quote_id, 
        "amount": quote.amount, 
        "unit": quote.unit
    })
    
    return {"status": "success", "quote": quote.to_dict()}
