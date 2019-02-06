# 1——2
# Add set_expire method.

# 1_1
# Add reminder for how to use get_oreder() filter, revised 2019-01-11
# Clearify codes in the private class
# Add docstring for methods.
# 
# To use filter in the get_order(), first create a json
# open_filter = json.dumps({"open": True})
# get_order(count=1, filter=open_filter)

import requests
import json
from urllib.parse import urlencode
import hmac
import hashlib
import time


class SpiralPublic:
    # base_url = ''
    __response_text = ''
    # __result = []
    
    def __init__(self, url):
        self.base_url = url
    
    def __get_public(self, url):
        try:
            response = requests.get(url=url)
            self.__response_text = response.text
        except requests.RequestException:
            print('Request Error.')
    
    def get_currencies(self):
        """Fetch exchange currencies information."""
        self.__get_public(self.base_url+'currencies')
        return json.loads(self.__response_text)['data']
    
    def get_products(self):
        """Fetch exchange production information."""
        self.__get_public(self.base_url+'products')
        return json.loads(self.__response_text)['data']
    
    def get_klines(self, symbol, period, limit):
        """
        symbol: string, 
        period: integer, e.g, 1, 5, 15, in minutes unit
        limit: integer, results to fetch, range 1-500
        """
        query = {'symbol': '{:s}'.format(symbol), 'period': period, 'limit': limit}
        k_url = self.base_url + 'klines' + '?' + urlencode(query)
        self.__get_public(k_url)
        return json.loads(self.__response_text)['data']
    
    def get_orderbook(self, symbol, limit):
        """
        symbol: string
        limit: integer, Min = 0, Max = 1000. Valid values: 0, 5, 10, 20, 50, 100, 1000. For limit = 0, full order book will be returned.
        """
        query = {'symbol': '{:s}'.format(symbol), 'limit': limit}
        o_url = self.base_url + 'orderbook' + '?' + urlencode(query)
        self.__get_public(o_url)
        return json.loads(self.__response_text)
    
    def get_trades(self, count, symbol='', start=None, reverse=None, start_time=None, end_time=None):
        """
        symbol: string,  Trading symbol name
        start: integer,  Offset of trades start to fetch
        count: integer,  REQUIRED Number of trades to fetch. Range: 1 - 1000
        reverse: boolean,  Whether sort results in create time descend
        start_time: integer,  UNIX timestamp, in seconds. Filter trades whose create time after start_time
        end_time: integer,  UNIX timestamp, in seconds. Filter trades whose create time before end_time
        """
        query = {
            'symbol': '{:s}'.format(symbol), 
            'count': count,
            'start': start,
            'reverse': reverse,
            'start_time': start_time,
            'end_time': end_time
        }
        t_url = self.base_url + 'trades' + '?' + urlencode(query)
        self.__get_public(t_url)
        return json.loads(self.__response_text)['trades']


class SpiralPrivate:
    # __response_text = ''
    
    def __init__(self, public_key, private_key, base_url, base_path):
        self.__public_key = public_key
        self.__private_key = private_key
        self.__base_url = base_url
        self.__base_path = base_path
    

    def set_expire_time(self, expire_time):
        self.expire_time = expire_time

        
    def __response(self, url, headers, verb, json_data=None):
        try:
            if verb == 'GET':
                response = requests.get(url=url, headers=headers)
            elif verb == 'POST':
                response = requests.post(url=url, headers=headers, data=json_data)
            elif verb == 'DELETE':
                response = requests.delete(url=url, headers=headers)
            return response
        except requests.RequestException:
            return 'Request error'

    
    def __response_return(self, dict_key, response_text):
        result = json.loads(response_text)
        if dict_key not in result:
            return result
        else:
            return result[dict_key]

            
    def __auth_response(self, verb, path_end, query_data=None, data=None):
        expire = int(round(time.time()) + self.expire_time)
        if verb != 'POST':
            if query_data is None:
                path = self.__base_path + path_end
                url = self.__base_url + path_end
            else:
                path = self.__base_path + path_end + '?' + urlencode(query_data)
                url = self.__base_url + path_end + '?' + urlencode(query_data)
            message = verb + path + str(expire)
        else:
            path = self.__base_path + path_end
            url = self.__base_url + path_end
            message = verb + path + str(expire) + json.dumps(data) 
        
        # Test output
        # print(url)
        # print(message)
        
        # signature method, detailed information can be found at bitmex api authentication page
        signature = hmac.new(bytes(self.__private_key, 'utf8'), bytes(message, 'utf8'), digestmod=hashlib.sha256).hexdigest()

        get_auth_headers = {
            'api-key': self.__public_key,
            'api-expires': str(expire),
            'api-signature': signature,
            # 'Content-Type': 'application/json'
        }

        if verb == 'POST':
            get_auth_headers['Content-Type'] = 'application/json'
        
        # Post data should be str or use json module to dump a json
        response = self.__response(url=url, headers=get_auth_headers, verb=verb, json_data=json.dumps(data))
        return response

        
    def get_wallet_balance(self, currency=''):
        """
        Fetch account wallet balances.

        currency: string, fetch all wallet balances if empty.
        """
        if currency != '':
            query_data = {'currency': currency}
        else:
            query_data = None
            
        response = self.__auth_response(verb='GET', path_end='/wallet/balances', query_data=query_data)
        return self.__response_return(dict_key='data', response_text=response.text)
    

    def get_myTrades(self, count, symbol='', start='', reverse='', start_time='', end_time=''):
        """
        Fetch private trades.

        count: int; REQUIRED, number of trades to fetch. Range: 1 - 1000;
        symbol: str; trading symbol name;
        start: int; offset of trades start to fetch;
        reverse: bool; if True, sort the results in time descend, most recent trades come first;
        start_time: int; UNIX timestamp, in seconds, filter trades that are created after start_time;
        end_time: int; UNIX timestamp, in seconds, filter trades that are created before start_time.
        """
        query_data={
            'count': count,
            'symbol': symbol,
            'start': start,
            'reverse': reverse,
            'start_time': start_time,
            'end_time': end_time
        }
        
        response = self.__auth_response(verb='GET', path_end='/myTrades', query_data=query_data)
        return self.__response_return(dict_key='trades', response_text=response.text)
    

    def get_order(self, count, symbol='', side='', reverse='', filter='', start_time='', end_time=''):
        """
        Fetch private orders.

        count: int; REQUIRED, number of orders to fetch. Range: 1 - 1000;
        symbol: str; trading symbol name;
        side: str; "bid" or "ask";
        reverse: bool; if True, sort the results in time descend, most recent trades come first;
        filter: str; JSON string, use like json.dumps({"open": True}), if not given, will return all orders, if set to False, only return close orders;
        start_time: int; UNIX timestamp, in microseconds, filter trades that are created after start_time;
        end_time: int; UNIX timestamp, in microseconds, filter trades that are created before start_time.
        """
        query_data={
            'count': count,
            'symbol': symbol,
            'side': side,
            'reverse': reverse,
            'filter': filter,
            'start_time': start_time,
            'end_time': end_time
        }
        
        response = self.__auth_response(verb='GET', path_end='/order', query_data=query_data)
        return self.__response_return(dict_key='orders', response_text=response.text)
    

    def __post_order(self, symbol, order_type, price, quantity, side, clt_ord_id=''):
        """
        A universal method to give orders according to the api.
        All params for POST method should be str.
        """
        data={
            'symbol': symbol,
            'type': order_type,
            'price': price,
            'quantity': quantity, # Avoid using scientific notation when formatting as a string.
            'side': side,
            'clt_ord_id': clt_ord_id
        }
        # Test output
        # print(str(data).replace("'", '"'))
        
        response = self.__auth_response(verb='POST', path_end='/order', data=data) # data=str(data).replace("'", '"')
        return self.__response_return(dict_key='orders', response_text=response.text)
    

    # Define buy and sell, market and limit
    def market_buy(self, symbol, quantity, clt=''):
        """
        Place a marekt buy order.

        symbol: str; symbol name;
        quantity: int/float; order quantity;
        clt: str; Client Order ID. This id will come back on the order and any related executions. \
        Should only contains alphanumeric characters, underscore, hyphen and colon
        """
        response = self.__post_order(symbol=symbol, order_type='market', price=0, quantity=quantity, side='bid', clt_ord_id=clt)
        return response
    

    def market_sell(self, symbol, quantity, clt=''):
        """
        Place a market sell order.

        symbol: str; symbol name;
        quantity: int/float; order quantity;
        clt: str; Client Order ID. This id will come back on the order and any related executions. \
        Should only contains alphanumeric characters, underscore, hyphen and colon
        """
        response = self.__post_order(symbol=symbol, order_type='market', price=0, quantity=quantity, side='ask', clt_ord_id=clt)
        return response
    

    def limit_buy(self, symbol, price, quantity, clt=''):
        """
        Place a limit buy order.
        
        symbol: str; symbol name;
        price: int/float; order price;
        quantity: int/float; order quantity;
        clt: str; Client Order ID. This id will come back on the order and any related executions. \
        Should only contains alphanumeric characters, underscore, hyphen and colon.
        """
        response = self.__post_order(symbol=symbol, order_type='limit', price=price, quantity=quantity, side='bid', clt_ord_id=clt)
        return response
    

    def limit_sell(self, symbol, price, quantity, clt=''):
        """
        Place a limit sell order.

        symbol: str; symbol name;
        price: int/float; order price;
        quantity: int/float; order quantity;
        clt: str; Client Order ID. This id will come back on the order and any related executions. \
        Should only contains alphanumeric characters, underscore, hyphen and colon.
        """
        response = self.__post_order(symbol=symbol, order_type='limit', price=price, quantity=quantity, side='ask', clt_ord_id=clt)
        return response
    

    def delete_order(self, order_id):
        """
        Cancel specified order.

        order_id: str; numeric order id.
        """
        query_data = {'order_id': order_id}
        response = self.__auth_response(verb='DELETE', path_end='/order', query_data=query_data)
        return response.text
    

    def delete_all_order(self, symbol='', filter=''):
        """
        Cancel all orders.

        symbol: str; cancel order for specified symbol, if not given delete all orders.
        filter: str; JSON string; json.dumps("side": String), String can be "buy" or "sell", \
        delete all buy or sell orders.
        """
        if symbol != '' and filter != '':
            query_data = {'symbol': symbol, 'filter': filter}
        else:
            query_data = None
            
        response = self.__auth_response(verb='DELETE', path_end='/order/all', query_data=query_data)
        return response.text
