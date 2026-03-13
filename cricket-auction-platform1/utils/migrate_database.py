"""
Database migration script.
Adds new fields to existing player documents without breaking data.
"""
from pymongo import MongoClient
from datetime import datetime, timezone
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings


def migrate_players():
    """Migrate player documents to add new fields."""
    client = MongoClient(settings.DATABASE_URL)
    db = client[settings.DB_NAME]
    
    print("🔄 Starting player migration...")
    
    # Get all players
    players = list(db.players.find({}))
    print(f"📊 Found {len(players)} players")
    
    updated_count = 0
    
    for player in players:
        update_fields = {}
        
        # Add role field if missing (map from old category if possible)
        if "role" not in player:
            # Try to infer from old data
            old_category = player.get("category", "")
            if old_category in ["Batter", "Batsman"]:
                update_fields["role"] = "Batsman"
            elif old_category in ["Bowler"]:
                update_fields["role"] = "Bowler"
            elif old_category in ["All-rounder", "All-Rounder"]:
                update_fields["role"] = "All-Rounder"
            elif old_category in ["Wicket-keeper", "Wicketkeeper"]:
                update_fields["role"] = "Wicketkeeper"
            else:
                update_fields["role"] = None
        
        # Add category field if missing (map from old affiliation_role)
        if "category" not in player:
            affiliation = player.get("affiliation_role")
            if affiliation in ["Faculty", "Student", "Alumni"]:
                update_fields["category"] = affiliation
            else:
                update_fields["category"] = None
        
        # Add image_path if missing
        if "image_path" not in player:
            update_fields["image_path"] = None
        
        # Add auction_round if missing
        if "auction_round" not in player:
            update_fields["auction_round"] = 1
        
        # Add updated_at if missing
        if "updated_at" not in player:
            update_fields["updated_at"] = player.get("created_at", datetime.now(timezone.utc))
        
        # Update if there are fields to add
        if update_fields:
            db.players.update_one(
                {"_id": player["_id"]},
                {"$set": update_fields}
            )
            updated_count += 1
    
    print(f"✅ Updated {updated_count} players")
    
    # Create indexes
    print("🔄 Creating indexes...")
    db.players.create_index("role")
    db.players.create_index("category")
    db.players.create_index("status")
    db.players.create_index("auction_round")
    print("✅ Indexes created")
    
    client.close()
    print("✨ Migration complete!")


def migrate_auction_config():
    """Add auction_round to config."""
    client = MongoClient(settings.DATABASE_URL)
    db = client[settings.DB_NAME]
    
    print("🔄 Migrating auction config...")
    
    config = db.config.find_one({"key": "auction"})
    if config and "auction_round" not in config:
        db.config.update_one(
            {"key": "auction"},
            {"$set": {"auction_round": 1}}
        )
        print("✅ Auction config updated")
    else:
        print("ℹ️  Auction config already up to date")
    
    client.close()


if __name__ == "__main__":
    print("=" * 50)
    print("🏏 Cricket Auction Database Migration")
    print("=" * 50)
    print()
    
    try:
        migrate_players()
        print()
        migrate_auction_config()
        print()
        print("=" * 50)
        print("✅ All migrations completed successfully!")
        print("=" * 50)
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
