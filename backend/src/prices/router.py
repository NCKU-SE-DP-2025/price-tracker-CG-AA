import asyncio
from typing import List

import httpx
from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter(prefix="/api/v1/prices", tags=["prices"])


@router.get("/necessities-price", response_model=List[dict])
async def get_necessities_prices(
    category: str = Query(None), commodity: str = Query(None)
):
    async with httpx.AsyncClient() as client:
        last_exception = None
        params = {}
        if category and commodity:
            params = {"CategoryName": category, "Name": commodity}
        else:
            params = {"CategoryName": "'", "Name": "'"}
        for _ in range(2):  # Try up to 2 times
            try:
                response = await client.get(
                    "https://opendata.ey.gov.tw/api/ConsumerProtection/NecessitiesPrice",
                    params=params,
                    timeout=10,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                last_exception = e
                await asyncio.sleep(1)
            except httpx.RequestError as e:
                last_exception = e
                await asyncio.sleep(1)

        if isinstance(last_exception, httpx.HTTPStatusError):
            raise HTTPException(
                status_code=last_exception.response.status_code,
                detail=f"External API error: {last_exception.response.text}",
            )
        if isinstance(last_exception, httpx.RequestError):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not fetch data from external API: "
                f"{last_exception}",
            )
