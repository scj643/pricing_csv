import csv
import re
import os
import json
import requests
from io import StringIO
from typing import Optional, List, Dict

EXPORT_KEYS = ['sku', 'desc', 'vend', 'dept', 'cash', 'trade', 'price', 'tax', 'id', 'new-price']  # Final output
STRIP_REGEX = re.compile(r'[ -_$!.]')  # Strip special characters


class GameConsole(object):
    def __init__(self, console_name: str, current: list, price_charting: list):
        """
        Collection of games in a console that attempts to match with price charting
        :param console_name: Console Name
        :param current: List of current items
        :param price_charting: List of price charting items
        """
        self.name = console_name
        self.price_charting = None
        self.current = None
        self.with_ids = None
        self.without_ids = None
        self.parse_list(current, price_charting)

    def parse_list(self, cur, pc):
        self.price_charting = [x for x in pc if str.lower(x['console-name']) == self.name.lower()]
        self.current = [x for x in cur if str.lower(x['dept']) == self.name.lower()]

    def get_ids(self, reg=STRIP_REGEX):
        self.with_ids = self.current
        for i in self.with_ids:
            for k in self.price_charting:
                if reg.sub('', k['product-name'].lower()) in reg.sub('', i['desc'].lower()):
                    i['id'] = k['id']
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

    def __repr__(self):
        return '<Console: {}>'.format(self.name)


class PriceChartingItem(object):
    def __init__(self, item_dict: Dict):
        self.item_dict = item_dict

    @property
    def console(self):
        return self.item_dict['console-name']

    @property
    def product(self):
        return self.item_dict['product-name']

    @property
    def loose_price(self):
        return money_to_float(self.item_dict['loose-price'])

    @property
    def complete_price(self):
        return money_to_float(self.item_dict['cib-price'])


class PriceChartingCollection(object):
    def __init__(self, url: Optional[str] = None, csv_list: Optional[List[PriceChartingItem]] = None,
                 csv_file: Optional[str] = None):
        """
        A collection of items that are received from price charting
        :param url: Grab data from URL
        :param csv_list: Use a pre made dictionary list
        :param csv_file: Use a file object
        """
        if csv_file:
            p_file = open(csv_file, 'r', newline='')
            p_reader = csv.DictReader(p_file)
            self.items = [PriceChartingItem(x) for x in p_reader]
        if csv_list:
            self.items = [PriceChartingItem(x) for x in csv_list]
        if url:
            r = requests.get(url)
            file_buffer = StringIO(r.content.decode('utf-8'))
            p_reader = csv.DictReader(file_buffer)
            self.items = [PriceChartingItem(x) for x in p_reader]
 
    def __repr__(self):
        return '<PriceChartingCollection>'


class GamestopItem(object):
    def __init__(self, item_dict: dict):
        self.item_dict = item_dict


class InventoryCollection(object):
    def __init__(self, csv_list: list = None, csv_file: str = None):
        if csv_file:
            i_file = open(csv_file, 'r', newline='')
            i_reader = csv.DictReader(i_file)
            self.items = [InventoryItem(x) for x in i_reader]
        if csv_list:
            self.items = [InventoryItem(x) for x in csv_list]


class InventoryItem(object):
    def __init__(self, item_dict: dict):
        self.item_dict = item_dict

    @property
    def sku(self):
        return self.item_dict['sku']

    @property
    def dept(self):
        return self.item_dict['dept']
    
    @property
    def desc(self):
        return self.item_dict['desc']

    @property
    def cash(self):
        return self.item_dict['cash']

    @property
    def trade(self):
        return self.item_dict['trade']

    @property
    def price(self):
        return self.item_dict['price']

    def __repr__(self):
        return '<InventoryItem: {} @ ${}>'.format(self.desc, self.price)


def get_consoles_price_charting(plist):
    output = []
    for i in plist:
        if i['console-name'] not in output:
            output += [i['console-name']]
    return output


def money_to_float(money_string: str) -> float:
    return float(STRIP_REGEX.sub('', money_string))


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
