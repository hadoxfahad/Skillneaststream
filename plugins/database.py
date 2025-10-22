# plugins/database.py
from pymongo import MongoClient
import motor.motor_asyncio
from info import MONGODB_URI

# Synchronous client for 'playscount' collection
client = MongoClient(MONGODB_URI)
db_playscount_collection = client['videoplays']['playscount'] # Direct access to collection

# --- Synchronous Database Functions (for playscount) ---

# This function adds a new record or increments the count
def add_or_update_visit(user: int, count_increment: int):
    """
    Records a visit by incrementing the count for a user.
    If the user does not exist, a new entry is created.
    """
    db_playscount_collection.update_one(
        {"user": user},
        {"$inc": {"count": count_increment}, "$setOnInsert": {"withdraw": False}},
        upsert=True # Creates the document if it doesn't exist
    )

# If you still want a `record_visit` that overwrites (not recommended for play counts)
# but to avoid import error for now, it's included.
# Ideally, you'd use add_or_update_visit everywhere you want to track plays.
def record_visit(user: int, count: int):
    """
    (Legacy/Overwrite) Records a visit by setting the count for a user.
    If the user does not exist, a new entry is created.
    """
    db_playscount_collection.update_one(
        {"user": user},
        {"$set": {"count": count, "withdraw": False}}, # Overwrites count, sets withdraw to False
        upsert=True
    )


def record_withdraw(user: int, withdraw_status: bool):
    """
    Records the withdrawal status for a user.
    """
    db_playscount_collection.update_one(
        {"user": user},
        {"$set": {"withdraw": withdraw_status}}
    )

def get_count(user: int):
    """
    Retrieves the total count (video plays) for a user.
    """
    existing_visit = db_playscount_collection.find_one({
        "user": user
    })
    if existing_visit:
        return existing_visit.get("count", 0) # Default to 0 if 'count' field is missing
    else:
        return 0 # Return 0 for non-existent user

def get_withdraw(user: int):
    """
    Retrieves the withdrawal status for a user.
    """
    existing_visit = db_playscount_collection.find_one({
        "user": user
    })
    if existing_visit:
        return existing_visit.get("withdraw", False) # Default to False if 'withdraw' field is missing
    else:
        return False # Return False for non-existent user

def reset_user_plays_and_withdraw_status(user: int):
    """
    Resets a user's video play count to 0 and withdrawal status to False.
    This is intended for use after a successful withdrawal or cancellation.
    """
    result = db_playscount_collection.update_one(
        {"user": user},
        {"$set": {"count": 0, "withdraw": False}}
    )
    return result.modified_count > 0 # Returns True if a document was modified

# Assign `record_visits` to the reset function for clarity in start.py
record_visits = reset_user_plays_and_withdraw_status


# --- Asynchronous Database Class for User Profiles ---

class Database: # Combined Database and Database2 for user profiles
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users # Collection for user profiles

    def new_user(self, id, name):
        return dict(
            id = id,
            name = name,
            b_name = None,
            c_link = None,
        )

    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)

    async def is_user_exist(self, id):
        user = await self.col.find_one({'id': int(id)})
        return bool(user)

    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count

    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})

    async def set_name(self, id, name):
        await self.col.update_one({'id': int(id)}, {'$set': {'b_name': name}})

    async def get_name(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('b_name')

    async def set_link(self, id, link):
        await self.col.update_one({'id': int(id)}, {'$set': {'c_link': link}})

    async def get_link(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('c_link')

# Instantiate the Database classes
checkdb = Database(MONGODB_URI, "TechVJVideoPlayerBot") # Assuming this is for basic user existence check
db = Database(MONGODB_URI, "VJVideoPlayerBot") # Assuming this is for setting/getting user profile data
