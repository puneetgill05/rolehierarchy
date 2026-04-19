# import hashlib
# import json
# from typing import Set
#
#
# class NSet(Set):
#     def __init__(self):
#         super().__init__()
#
#     def addAll(self, items):
#         for item in items:
#             self.add(item)
#
#     def get(self, item):
#         for it in self:
#             if item == it:
#                 return it
#         return None
#
#     def get_first(self):
#         for it in self:
#             return it
#
#     def __str__(self):
#         ret = ''
#         for item in self:
#             ret += ' ' + str(item)
#         return ret
#
#     def __eq__(self, other):
#         for item in other:
#             if item not in self:
#                 return False
#         for item in self:
#             if item not in other:
#                 return False
#         return True
#
#     def __hash__(self):
#         encoded = json.dumps(self, sort_keys=True).encode()
#         return hashlib.sha256(encoded).hexdigest()