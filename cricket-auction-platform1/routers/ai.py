"""
AI router for player price prediction.
Provides ML-powered price predictions for players.
"""
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from typing import Optional

from database import db
from core.security import get_current_user
from ai.price_prediction import price_predictor

router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/predict-price/{player_id}")
async def predict_player_price(
    player_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Predict auction price for a player using ML model.
    
    Uses player statistics to predict likely auction price.
    """
    try:
        pid = ObjectId(player_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid player ID")
    
    # Get player
    player = db.players.find_one({"_id": pid})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Extract player statistics (with defaults)
    batting_average = float(player.get("batting_average", 0))
    strike_rate = float(player.get("strike_rate", 0))
    wickets = int(player.get("wickets", 0))
    matches_played = int(player.get("matches_played", 0))
    age = int(player.get("age", 25))
    previous_price = float(player.get("final_bid", 0) or player.get("base_price", 0) or 0)
    
    # Predict price
    prediction = price_predictor.predict_price(
        batting_average=batting_average,
        strike_rate=strike_rate,
        wickets=wickets,
        matches_played=matches_played,
        age=age,
        previous_price=previous_price
    )
    
    return {
        "ok": True,
        "player_id": player_id,
        "player_name": player.get("name"),
        "predicted_price": prediction["predicted_price"],
        "confidence": prediction["confidence"],
        "method": prediction["method"],
        "input_features": {
            "batting_average": batting_average,
            "strike_rate": strike_rate,
            "wickets": wickets,
            "matches_played": matches_played,
            "age": age,
            "previous_price": previous_price
        }
    }


@router.post("/predict-price-custom")
async def predict_custom_price(
    batting_average: float = 0.0,
    strike_rate: float = 0.0,
    wickets: int = 0,
    matches_played: int = 0,
    age: int = 25,
    previous_price: float = 0.0,
    current_user: dict = Depends(get_current_user)
):
    """
    Predict price with custom player statistics.
    
    Useful for estimating prices for hypothetical players.
    """
    prediction = price_predictor.predict_price(
        batting_average=batting_average,
        strike_rate=strike_rate,
        wickets=wickets,
        matches_played=matches_played,
        age=age,
        previous_price=previous_price
    )
    
    return {
        "ok": True,
        "predicted_price": prediction["predicted_price"],
        "confidence": prediction["confidence"],
        "method": prediction["method"],
        "input_features": {
            "batting_average": batting_average,
            "strike_rate": strike_rate,
            "wickets": wickets,
            "matches_played": matches_played,
            "age": age,
            "previous_price": previous_price
        }
    }


@router.get("/model-info")
async def get_model_info(current_user: dict = Depends(get_current_user)):
    """Get information about the ML model."""
    return {
        "ok": True,
        "model_loaded": price_predictor.model is not None,
        "model_type": "RandomForestRegressor" if price_predictor.model else "Heuristic",
        "features": price_predictor.feature_names,
        "description": "ML model for predicting player auction prices based on statistics"
    }
