"""
AI-powered player price prediction using machine learning.
Predicts auction prices based on player statistics and historical data.
"""
import pickle
import os
from typing import Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Model path
MODEL_PATH = Path(__file__).parent / "model.pkl"


class PricePredictionModel:
    """Machine learning model for predicting player auction prices."""
    
    def __init__(self):
        self.model = None
        self.feature_names = [
            'batting_average',
            'strike_rate',
            'wickets',
            'matches_played',
            'age',
            'previous_price'
        ]
        self.load_model()
    
    def load_model(self):
        """Load trained model from disk."""
        try:
            if MODEL_PATH.exists():
                with open(MODEL_PATH, 'rb') as f:
                    self.model = pickle.load(f)
                logger.info("✅ Price prediction model loaded successfully")
            else:
                logger.warning("⚠️ Model file not found. Train model first using train_model.py")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model = None
    
    def predict_price(
        self,
        batting_average: float = 0.0,
        strike_rate: float = 0.0,
        wickets: int = 0,
        matches_played: int = 0,
        age: int = 25,
        previous_price: float = 0.0
    ) -> Dict[str, Any]:
        """
        Predict player auction price.
        
        Args:
            batting_average: Career batting average
            strike_rate: Career strike rate
            wickets: Total wickets taken
            matches_played: Total matches played
            age: Player age
            previous_price: Previous auction price (if any)
        
        Returns:
            Dictionary with predicted_price and confidence
        """
        if self.model is None:
            # Fallback: Simple heuristic-based prediction
            return self._fallback_prediction(
                batting_average, strike_rate, wickets,
                matches_played, age, previous_price
            )
        
        try:
            # Prepare features
            features = [[
                batting_average,
                strike_rate,
                wickets,
                matches_played,
                age,
                previous_price
            ]]
            
            # Predict
            predicted_price = self.model.predict(features)[0]
            
            # Calculate confidence (using model's feature importances if available)
            confidence = self._calculate_confidence(
                batting_average, strike_rate, wickets,
                matches_played, age, previous_price
            )
            
            return {
                "predicted_price": float(max(0, predicted_price)),
                "confidence": confidence,
                "method": "ml_model"
            }
            
        except Exception as e:
            logger.error(f"Error predicting price: {e}")
            return self._fallback_prediction(
                batting_average, strike_rate, wickets,
                matches_played, age, previous_price
            )
    
    def _fallback_prediction(
        self,
        batting_average: float,
        strike_rate: float,
        wickets: int,
        matches_played: int,
        age: int,
        previous_price: float
    ) -> Dict[str, Any]:
        """
        Fallback heuristic-based prediction when ML model is unavailable.
        """
        base_price = 50000  # Base price
        
        # Batting contribution
        batting_score = (batting_average * 1000) + (strike_rate * 500)
        
        # Bowling contribution
        bowling_score = wickets * 5000
        
        # Experience bonus
        experience_bonus = min(matches_played * 1000, 50000)
        
        # Age factor (peak age 25-30)
        if 25 <= age <= 30:
            age_factor = 1.2
        elif 20 <= age < 25 or 30 < age <= 35:
            age_factor = 1.0
        else:
            age_factor = 0.8
        
        # Previous price influence
        previous_influence = previous_price * 0.3 if previous_price > 0 else 0
        
        # Calculate predicted price
        predicted_price = (
            base_price +
            batting_score +
            bowling_score +
            experience_bonus +
            previous_influence
        ) * age_factor
        
        # Confidence based on data completeness
        data_points = sum([
            batting_average > 0,
            strike_rate > 0,
            wickets > 0,
            matches_played > 0,
            previous_price > 0
        ])
        confidence = min(0.5 + (data_points * 0.1), 0.9)
        
        return {
            "predicted_price": float(max(base_price, predicted_price)),
            "confidence": confidence,
            "method": "heuristic"
        }
    
    def _calculate_confidence(
        self,
        batting_average: float,
        strike_rate: float,
        wickets: int,
        matches_played: int,
        age: int,
        previous_price: float
    ) -> float:
        """Calculate prediction confidence score (0-1)."""
        # Base confidence
        confidence = 0.7
        
        # Increase confidence if more data is available
        if batting_average > 0:
            confidence += 0.05
        if strike_rate > 0:
            confidence += 0.05
        if wickets > 0:
            confidence += 0.05
        if matches_played > 10:
            confidence += 0.05
        if previous_price > 0:
            confidence += 0.05
        
        # Decrease confidence for extreme values
        if age < 18 or age > 40:
            confidence -= 0.1
        if matches_played < 5:
            confidence -= 0.1
        
        return min(max(confidence, 0.3), 0.95)


# Global model instance
price_predictor = PricePredictionModel()
