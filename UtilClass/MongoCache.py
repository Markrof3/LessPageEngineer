import pymongo

from datetime import datetime

from LessPageEngineering.Settings import MONGO_HOST, MONGO_DB, MONGO_CONNECT

class MongoCache:
    def __init__(self):
        self.mong_con = pymongo.MongoClient(host=MONGO_HOST)[MONGO_DB][MONGO_CONNECT]

    def dump_data(self, key, source_dict, replace):
        assert isinstance(source_dict, dict), "source_dict非字典"
        source_dict.update({
            'key': key,
            'update_time': datetime.now()
        })
        if not self.mong_con.count_documents({'key': key}) > 0:
            self.mong_con.insert_one(source_dict)
        else:
            if replace:
                self.mong_con.delete_one({'key': key})
                self.mong_con.insert_one(source_dict)
    def load_data(self, key):
        if not key or not isinstance(key, str):
            return None
        return self.mong_con.find_one({'key': key})
