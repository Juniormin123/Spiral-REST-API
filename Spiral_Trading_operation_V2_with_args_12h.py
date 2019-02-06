import Spiral_Trading_api_wrap_V1_2 as ST
import pandas as pd
import time
import os
import sys
# from sys import argv
from stockstats import StockDataFrame


# Setup
os.chdir(sys.path[0])

api_public = 'cba7dad1a02e40beb5470febcf730016'
api_secret = '5b5c1008b8d64b029e208052172a404e'
base_url = 'https://api.spiral.exchange/api/v1'
private_base_path = '/api/v1'

st_public = ST.SpiralPublic(url=base_url+'/')
st_private = ST.SpiralPrivate(base_path=private_base_path,
                              base_url=base_url, private_key=api_secret, public_key=api_public)


def current_position(symbol):
    response = st_private.get_wallet_balance(currency=symbol)
    result_dict = {'in_use': float(
        response[0]['available']), 'locked': float(response[0]['locked'])}
    return result_dict


# Calculate ma, ema, bar, boll using stocktats library
def calculate_macd_boll(klines_response, boll_bar, output_df=False):
    klines_data_dict = {
        'open_time': '',
        'open': '',
        'high': '',
        'low': '',
        'close': '',
        'volume': '',
        'close_time': '',
        'future_usage': '',
        'no_of_trades': ''
    }
    for field_order, field_name in enumerate(klines_data_dict):
        klines_data_dict[field_name] = [
            float(i[field_order]) for i in klines_response]

    klines_df = pd.DataFrame(klines_data_dict)
    klines_df['open_time'] = pd.to_datetime(
        klines_df.open_time.values, unit='ms', utc=1).tz_convert('Asia/Shanghai')
    klines_df['close_time'] = pd.to_datetime(
        klines_df.open_time.values, unit='ms', utc=1).tz_convert('Asia/Shanghai')

    # klines_df.sort_values(by='open_time', ascending=True, inplace=True)
    result = [klines_df['close'].tail(1).values[0]]
    dict_list = ['close']
    stock_stats = StockDataFrame.retype(klines_df)

    if boll_bar.lower() == 'macd':
        macd_df = pd.DataFrame(
            data=[stock_stats['macd'], stock_stats['macds'], stock_stats['macdh']]).T
        # klines_df_result = klines_df.join(macd_df)
        dict_list += ['macd', 'macds']
        result += [macd_df.tail(1).iloc[0, 0], macd_df.tail(1).iloc[0, 1]]

    elif boll_bar.lower() == 'boll':
        boll_df = pd.DataFrame(
            data=[stock_stats['boll'], stock_stats['boll_lb'], stock_stats['boll_ub']]).T
        # klines_df_result = klines_df.join(boll_df)
        dict_list += ['boll', 'boll_lb', 'boll_ub']
        result += [boll_df.tail(1).iloc[0, 0],
                   boll_df.tail(1).iloc[0, 1], boll_df.tail(1).iloc[0, 2]]

    if output_df:
        return klines_df
    else:
        return dict(zip(dict_list, result))


# Define trade signal here
# initial_state should be the previous kline data with same format as current state
def signal(initial_state, symbol, boll_macd, kline_period):
    current_state = calculate_macd_boll(st_public.get_klines(
        symbol=symbol, limit=500, period=kline_period), boll_macd)
    op = 'no signal'

    if boll_macd.lower() == 'macd':
        if initial_state['macd'] > initial_state['macds'] and current_state['macd'] < current_state['macds']:
            op = 'sell'
        elif initial_state['macd'] < initial_state['macds'] and current_state['macd'] > current_state['macds']:
            op = 'buy'

    if boll_macd.lower() == 'boll':
        if initial_state['close'] > initial_state['boll_ub'] and current_state['close'] < current_state['boll_ub']:
            op = 'sell'
        elif initial_state['close'] < initial_state['boll_lb'] and current_state['close'] > current_state['boll_lb']:
            op = 'buy'

    return current_state, op


def log(text, file_name='trade_log_v2.txt'):
    with open(file_name, 'a+', encoding='utf-8') as log_writer:
        log_writer.write(text + '\n')
    print(text)


def trade(symbol, current_quote_pos, current_asset_pos, boll_macd, initial_state, kline_period, multiplier):

    order = 'No trade.'
    current_state_op = signal(initial_state, symbol, boll_macd, kline_period)
    op = current_state_op[1]
    current_state = current_state_op[0]

    if op == 'sell':
        order = st_private.market_sell(symbol, current_asset_pos*multiplier)
        time.sleep(0.5)
        order_cost = st_private.get_order(count=1, reverse=True)
        order['filled_price'] = order_cost[0]['filled_price']
        order['filled_quantity'] = order_cost[0]['filled_quantity']

    # if current_quote_pos >= price['close']*max_trade_quantity:
    elif op == 'buy':
        order = st_private.market_buy(symbol, (current_quote_pos/current_state['close'])*multiplier)
        time.sleep(0.5)
        order_cost = st_private.get_order(count=1, reverse=True)
        order['filled_price'] = order_cost[0]['filled_price']
        order['filled_quantity'] = order_cost[0]['filled_quantity']

    # Log ouput
    if boll_macd.lower() == 'boll':
        log('Close: {:2.2f}, boll: {:2.4f}, boll_lb: {:2.4f}, boll_ub: {:2.4f}'.format(current_state['close'],
                                                                                       current_state['boll'], current_state['boll_lb'], current_state['boll_ub']))

    elif boll_macd.lower() == 'macd':
        log('Close: {:2.2f}, macd: {:2.4f}, macds: {:2.4f}'.format(
            current_state['close'], current_state['macd'], current_state['macds']))

    return order


# Main
def main(quote, asset, process_time, expire_time, boll_macd, kline_period, multiplier):
    # quote = 'USDT'
    # asset = 'ETH'
    # ma1, ma2 = 5, 10

    end_time = time.time() + process_time

    symbol = asset + quote
    initial_state = calculate_macd_boll(st_public.get_klines(
        symbol=symbol, limit=500, period=kline_period), boll_macd)

    # Set expire time
    st_private.set_expire_time(expire_time)

    start_position = {quote: current_position(quote), asset: current_position(asset)}

    # For future pnl calculation
    # filled_price = read_last_filled()

    log('Start time: {:}'.format(time.strftime(
        '%Y-%m-%d %H:%M:%S', time.localtime(time.time()))))
    log('Mode: {:}'.format(boll_macd))
    log('Initial position: {:}: {:}; {:}: {:}'.format(
        quote, start_position[quote], asset, start_position[asset]))
    log('=' * 60)
    time.sleep(kline_period*60-1)

    while time.time() < end_time:

        quote_position = current_position(quote)['in_use']
        asset_position = current_position(asset)['in_use']

        log('Quote position: {:}, Asset position: {:}'.format(
            quote_position, asset_position))

        order_info = trade(symbol, quote_position, asset_position,
                           boll_macd, initial_state, kline_period, multiplier)

        if isinstance(order_info, dict):
            # filled_price += [order_info['filled_price'], order_info['filled_quantity'], order_info['side']]

            log('1 Trade, {:}'.format(time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime(time.time()))))
            log('order ID: {:}, filled_price: {:}, order_quantity: {:}, filled_quantity: {:}, side: {:}'.format(
                order_info['id'], order_info['filled_price'], order_info['quantity'], order_info['filled_quantity'],
                order_info['side']))
        else:
            log('{:} {:}'.format(order_info, time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime(time.time()))))
        log('=' * 60)

        # Update state for next trade condition
        initial_state = calculate_macd_boll(st_public.get_klines(
            symbol=symbol, limit=500, period=kline_period), boll_macd)
        time.sleep(kline_period*60-1)

    # Delete remaining orders
    st_private.delete_all_order()
    log('End time: {:}'.format(time.strftime(
        '%Y-%m-%d %H:%M:%S', time.localtime(time.time()))))
    log('Program End, all remaining orders deleted.')


if __name__ == '__main__':
    
    quote = 'USDT'
    asset = 'ETH'
    process_time = 43200
    expire = 10
    boll_macd = 'boll'
    kline_period = '1'
    multiplier = '0.4'

    main(quote, asset, int(process_time), int(expire), boll_macd, int(kline_period), float(multiplier))
