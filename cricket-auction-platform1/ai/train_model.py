"""
Train machine learning model for player price prediction.
Run this script to train the model using historical auction data.

Usage:
    python -m ai.train_model
"""
import pickle
import logging
from pathlib import Path
from typing import List, Tuple
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# Model path
MODEL_PATH = Path(__file__).parent / "model.pkl"


def generate_synthetic_training_data() -> Tuple[List[List[float]], List[float]]:
    """
    Generate synthetic training data for demonstration.
    In production, replace with actual historical auction data.
    
    Returns:
        Tuple of (features, prices)
    """
    import random
    
    features = []
    prices = []
    
    # Generate 200 synthetic player records
    for _ in range(200):
        # Features: batting_avg, strike_rate, wickets, matches, age, prev_price
        batting_avg = random.uniform(15, 55)
        strike_rate = random.uniform(80, 180)
        wickets = random.randint(0, 300)
        matches = random.randint(10, 200)
        age = random.randint(20, 38)
        prev_price = random.uniform(0, 100000)
        
        # Calculate synthetic price based on features
        price = (
            50000 +  # Base price
            batting_avg * 1500 +
            strike_rate * 400 +
            wickets * 3000 +
            matches * 800 +
            (30 - abs(age - 27)) * 2000 +  # Peak age bonus
            prev_price * 0.4 +
            random.uniform(-20000, 20000)  # Random noise
        )
        
        features.append([
            batting_avg,
            strike_rate,
            wickets,
            matches,
            age,
            prev_price
        ])
        prices.append(max(50000, price))
    
    return features, prices


def train_model():
    """Train RandomForestRegressor model."""
    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import mean_absolute_error, r2_score
        
        logger.info("🤖 Starting model training...")
        
        # Generate training data
        X, y = generate_synthetic_training_data()
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train model
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        
        logger.info("Training RandomForestRegressor...")
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        logger.info(f"✅ Model trained successfully!")
        logger.info(f"   Mean Absolute Error: ₹{mae:,.2f}")
        logger.info(f"   R² Score: {r2:.4f}")
        
        # Save model
        with open(MODEL_PATH, 'wb') as f:
            pickle.dump(model, f)
        
        logger.info(f"💾 Model saved to {MODEL_PATH}")
        
        # Feature importances
        feature_names = [
            'batting_average', 'strike_rate', 'wickets',
            'matches_played', 'age', 'previous_price'
        ]
        importances = model.feature_importances_
        
        logger.info("\n📊 Feature Importances:")
        for name, importance in sorted(
            zip(feature_names, importances),
            key=lambda x: x[1],
            reverse=True
        ):
            logger.info(f"   {name}: {importance:.4f}")
        
        return True
        
    except ImportError:
        logger.error(
            "❌ scikit-learn not installed. "
            "Install with: pip install scikit-learn"
        )
        return False
    except Exception as e:
        logger.error(f"❌ Error training model: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    success = train_model()
    sys.exit(0 if success else 1)
