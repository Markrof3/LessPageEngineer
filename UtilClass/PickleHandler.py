import pickle
import os
from datetime import datetime
class PickleHandler:

    def __init__(self, folder_path='.\\pickle\\'):
        self.folder_path = folder_path
        if not os.path.exists(self.folder_path):
            os.mkdir(self.folder_path)

    def dump(self, data, file_path):
        with open(os.path.join(self.folder_path , file_path + '.lpe').replace('/','~'), 'wb') as fp:
            pickle.dump(data, fp, protocol=pickle.HIGHEST_PROTOCOL)

    def read(self, file_path):
        with open(os.path.join(self.folder_path, file_path + '.lpe').replace('/','~'), 'rb') as fp:
            loaded_data  = pickle.loads(fp.read())
        return loaded_data

    def exist(self, key):
        return os.path.exists(os.path.join(self.folder_path, key + '.lpe').replace('/','~'))

    def dump_data(self, key, source_dict, replace):
        assert isinstance(source_dict, dict), "source_dict非字典"
        source_dict.update({
            'key': key,
            'update_time': datetime.now()
        })
        # 本地文件夹存在且replace不为True时，则不重新写入
        if not replace and self.exist(key):
            return
        self.dump(source_dict, key)

    def load_data(self, key):
        if not self.exist(key):
            return None
        return self.read(key)

# if __name__ == '__main__':
#     handler = PickleHandler(folder_path=r'E:\aaazzl\zzl\LessPageEngineeringServer\files')
#     data = handler.load_data('aHR0cHM6Ly93ZWIud2hhdHNhcHAuY29tLw==')
#     for i in data.items():
#         if i[0].startswith('http'):
#             if type(i[1]['body']) == bytes:
#                 i[1]['body'] = i[1]['body'].replace(b'var P=$.use_fbt_virtual_modules===!0&&N', b'window.b=F;window.d=H;var P=$.use_fbt_virtual_modules===!0&&N')
#             else:
#                 i[1]['body'] = i[1]['body'].replace('var P=$.use_fbt_virtual_modules===!0&&N', 'window.b=F;window.d=H;var P=$.use_fbt_virtual_modules===!0&&N')
#
#     handler.dump_data('aHR0cHM6Ly93ZWIud2hhdHNhcHAuY29tLw==', data, True)