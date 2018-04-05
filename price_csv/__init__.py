import csv
import re
import os
import json
import requests
from io import StringIO
from typing import Optional, List, Dict, Union
from collections import UserList, UserDict

EXPORT_KEYS = ['sku', 'desc', 'vend', 'dept', 'cash', 'trade', 'price', 'tax', 'id', 'new-price']  # Final output
STRIP_REGEX = re.compile(r'[ _$!.]')  # Strip special characters
STRIP_DASH_REGEX = re.compile(r'[ _$!.][^-]*$')


class InventoryItem(UserDict):
    def __init__(self, item_dict: dict):
        super(InventoryItem, self).__init__()
        self.data = item_dict

    @property
    def sku(self):
        return self.data['sku']

    @property
    def dept(self):
        return self.data['dept']

    @property
    def name(self):
        return self.data['desc']

    @property
    def cash(self):
        return self.data['cash']

    @property
    def trade(self):
        return self.data['trade']

    @property
    def price(self):
        return self.data['price']

    def __repr__(self):
        return '<InventoryItem: {} @ ${}>'.format(self.name, self.price)


class GamestopItem(UserDict):
    def __init__(self, item_dict: dict):
        super(GamestopItem, self).__init__()
        self.data = item_dict

    @property
    def name(self):
        return self.data['product-name']

    @property
    def price(self):
        return money_to_float(self.data['gamestop-price'])

    @property
    def trade_price(self):
        return money_to_float(self.data['gamestop-trade-price'])

    @property
    def id(self):
        return self.data['id']

    def __repr__(self):
        return '<GamestopItem: {} @ ${}>'.format(self.name, self.price)


class PriceChartingItem(UserDict):
    def __init__(self, item_dict: Dict):
        super(PriceChartingItem, self).__init__()
        self.data = item_dict

    @property
    def console(self):
        return self.data['console-name']

    @property
    def name(self):
        return self.data['product-name']

    @property
    def loose_price(self):
        return money_to_float(self.data['loose-price'])

    @property
    def complete_price(self):
        return money_to_float(self.data['cib-price'])

    def __repr__(self):
        return '<PriceChartingItem: {} @ ${}>'.format(self.name, self.complete_price)


class ItemCollection(UserList):
    def __init__(self, item_type: type,
                 url: Optional[str] = None, csv_list: List = None,
                 csv_file: Optional[str] = None):
        """
        Base class for Collection items
        :param item_type: The kind of item to be pushed to
        :param url: Grab data from URL
        :param csv_list: Use a pre made dictionary list
        :param csv_file: Use a file object
        """
        super(ItemCollection, self).__init__()
        if csv_file:
            p_file = open(csv_file, 'r', newline='')
            p_reader = csv.DictReader(p_file)
            self.data = [item_type(x) for x in p_reader]
        if csv_list:
            self.data = [item_type(x) for x in csv_list]
        if url:
            r = requests.get(url)
            file_buffer = StringIO(r.content.decode('utf-8'))
            p_reader = csv.DictReader(file_buffer)
            self.data = [item_type(x) for x in p_reader]


class PriceChartingCollection(ItemCollection):
    def __init__(self, url: Optional[str] = None, csv_list: List = None, csv_file: Optional[str] = None):
        super().__init__(PriceChartingItem, url, csv_list, csv_file)
 
    def __repr__(self):
        return '<PriceChartingCollection>'


class InventoryCollection(ItemCollection):
    def __init__(self, url: Optional[str] = None, csv_list: List = None, csv_file: Optional[str] = None):
        super().__init__(InventoryItem, url, csv_list, csv_file)

    def __repr__(self):
        return '<InventoryCollection>'


class GamestopCollection(ItemCollection):
    def __init__(self, url: Optional[str] = None, csv_list: List = None, csv_file: Optional[str] = None):
        super().__init__(InventoryItem, url, csv_list, csv_file)

    def __repr__(self):
        return '<GamestopCollection>'


class MatchingItems(object):
    def __init__(self, inventory_item: InventoryItem, other: Union[GamestopItem, PriceChartingItem]):
        self.inventory_item = inventory_item
        self.other = other
        self.matches = []
        self.matches += [self.other]

    # TODO add way to match multiple items using the length to determine how close they are
    @property
    def shorter_name(self):
        """
        Finds the item with the shorter name
        :return: string
        """
        if len(self.inventory_item.name) < len(self.other.name):
            return self.inventory_item.name
        else:
            return self.other.name

    def __repr__(self):
        return '<MatchingItems {}>'.format(self.shorter_name)


class GameCompare(object):
    def __init__(self, current: InventoryCollection, other: Union[PriceChartingCollection, GamestopCollection],
                 curkey: str, otherkey: str, matchvalue: Union[bool, str] = True):
        """
        Object that's the basis of GameConsole
        """
        self.current = current
        self.other = other
        self.without_ids = None
        self.with_ids = None
        self.matches = []
        self.parse(self.current, self.other, curkey, otherkey, matchvalue)

    def parse(self, cur: InventoryCollection, other: Union[GamestopCollection, PriceChartingCollection],
              curkey: str, otherkey: str, matchvalue: Union[bool, str] = True) -> None:
        """
        Parse the collections passed
        :param cur: Current inventory list
        :param other: Inventory list to compare
        :param curkey: key to compare on the current list
        :param otherkey: key to compare on the other list
        :param matchvalue: String to match with the keys
        :return: None
        """
        if type(matchvalue) == str:
            matchvalue = matchvalue.lower()
        self.current = [x for x in cur if str.lower(x[curkey]) == matchvalue]
        self.other = [x for x in other if str.lower(x[otherkey]) == matchvalue]

    def get_ids(self, reg=STRIP_REGEX):
        self.with_ids = self.current
        for i in self.with_ids:
            for k in self.other:
                if reg.sub('',  k.name.lower()) in reg.sub('', i.name.lower()):
                    print(reg.sub('',  k.name.lower()))
                    i['id'] = k['id']
                    self.matches += [MatchingItems(i, k)]
        self.without_ids = [x for x in self.with_ids if 'id' not in x.keys()]
        self.with_ids = [x for x in self.with_ids if 'id' in x.keys()]

    def write_with_ids(self, file_path):
        with open(file_path, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=EXPORT_KEYS)
            writer.writeheader()
            writer.writerows(self.with_ids)

    def write_without_ids(self, file_path):
        with open(file_path, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=EXPORT_KEYS)
            writer.writeheader()
            writer.writerows(self.without_ids)


class GameConsole(GameCompare):
    def __init__(self, current: InventoryCollection, other: PriceChartingCollection, name: str):
        self.name = name
        super(GameConsole, self).__init__(current, other, 'dept', 'console-name', name)

    def __repr__(self):
        return '<Console: {}>'.format(self.name)


def get_consoles_price_charting(plist):
    output = []
    for i in plist:
        if i['console-name'] not in output:
            output += [i['console-name']]
    return output


def money_to_float(money_string: str) -> Optional[float]:
    try:
        return float(re.sub('[$ ]', '', money_string))
    except ValueError:
        return None


def get_consoles_cur(clist: list):
    output = []
    for i in clist:
        if i['dept'] not in output:
            output += [i['dept']]
    return output


def get_conf():
    if os.path.exists('conf.json'):
        with open('conf.json', 'r') as f:
            conf = json.load(f)
    else:
        conf = None
        print('config not found at', os.getcwd())
        exit('Config not found')

    url = None
    try:
        url = conf['url']
    except TypeError:
        print('config not valid at', os.getcwd())
        exit('Config not valid')
    except KeyError:
        print('config not valid at', os.getcwd())
        exit('Config not valid')
    return url


def gamestop_to_ours(price: int):
    """
    Convert gamestop prices to our prices
    :param price: Gamestop Price
    :return: Our adjusted price
    """
    ours = None
    if price <= 7.99:
        ours = price
    if 7.99 < price <= 8.99:
        ours = str(7.99)
    if 9 < price <= 9.99:
        ours = str(8.99)
    if 10 < price <= 13.99:
        ours = str(10.99)
    if 14 < price <= 14.99:
        ours = str(11.99)
    if 15 < price <= 17.99:
        ours = str(14.99)
    if 18 < price <= 19.99:
        ours = str(15.99)
    if 20 < price <= 24.99:
        ours = str(21.99)
    if 25 < price <= 27.99:
        ours = str(23.99)
    if 28 < price <= 31.98:
        ours = str(25.99)
    if 31.99 < price <= 34.99:
        ours = str(31.99)
    if 35 < price <= 36.99:
        ours = str(33.99)
    if 37 < price <= 39.99:
        ours = str(35.99)
    if 40 < price <= 47.98:
        ours = str(37.99)
    if 47.99 < price <= 52.99:
        ours = str(47.99)
    if 52.99 < price:
        ours = str(round(price * 0.9) - 0.01)
    return ours
