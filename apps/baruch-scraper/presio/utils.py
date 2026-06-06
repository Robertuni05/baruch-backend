import hashlib


class Utils:

    def genId(description):
        obj = hashlib.md5()
        # print(f"description is {description}")
        obj.update(description.encode('utf-8'))
        return obj.hexdigest()
