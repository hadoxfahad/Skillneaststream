from pymongo import MongoClient
import motor.motor_asyncio
from info import MONGODB_URI

# Synchronous client for 'playscount' collection
client = MongoClient(MONGODB_URI)
db_sync = client['videoplays'] # Renamed to avoid conflict with async db object
collection = db_sync['playscount']

# --- Synchronous Database Functions (for playscount) ---

def add_or_update_visit(user: int, count_increment: int):
    """
    Records a visit by incrementing the count for a user.
    If the user does not exist, a new entry is created.
    """
    existing_visit = collection.find_one({
        "user": user
    })
    if not existing_visit:
        collection.insert_one({
            "user": user,
            "count": count_increment, # Start with the given increment
            "withdraw": False
        })
    else:
        # Increment the existing count
        collection.update_one({"user": user}, {"$inc": {"count": count_increment}})

def record_withdraw(user: int, withdraw_status: bool):
    """
    Records the withdrawal status for a user.
    """
    existing_visit = collection.find_one({
        "user": user
    })
    if existing_visit:
        user_data = {
            "withdraw": withdraw_status
        }
        collection.update_one({"user": user}, {"$set": user_data})

def get_count(user: int):
    """
    Retrieves the total count (video plays) for a user.
    """
    existing_visit = collection.find_one({
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
    existing_visit = collection.find_one({
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
    existing_visit = collection.find_one({
        "user": user
    })
    if existing_visit:
        collection.update_one(
            {"user": user},
            {"$set": {"count": 0, "withdraw": False}}
        )
        return True
    return False

# You can use the more descriptive name 'add_or_update_visit'
# or keep 'record_visit' as an alias if you prefer.
# For simplicity and clarity in the context of incrementing, I've updated the usage below.
# If you want to keep the old 'record_visit' behavior (overwrite count), then define `record_visits` separately.

# For the purpose of the 'notify' command, `record_visits` should likely
# reset the count, which `reset_user_plays_and_withdraw_status` will do.
record_visits = reset_user_plays_and_withdraw_status


# --- Asynchronous Database Class for User Profiles ---

class Database2: # This seems to be for general user data (name, link)
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users

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

checkdb = Database2(MONGODB_URI, "TechVJVideoPlayerBot")

class Database: # This also seems to be for general user data, potentially a duplicate or a more comprehensive one.
    # It's generally better to have one async database class for user profiles
    # and use it consistently, rather than 'Database' and 'Database2'.
    # I'll assume 'db' (instance of Database) is the primary one for user profiles.

    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users

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

db = Database(MONGODB_URI, "VJVideoPlayerBot")
