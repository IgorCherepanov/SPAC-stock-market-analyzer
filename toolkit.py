import http.client
import requests
import pandas as pd
import io
from datetime import datetime, timedelta
import matplotlib as plt
import matplotlib.dates as mdates

def connect(key):
    '''
    Connect to the Yahoo Finance server. We use here API from Rakuten:
    https://english.api.rakuten.net/apidojo/api/yahoo-finance1
    '''
    conn = http.client.HTTPSConnection("apidojo-yahoo-finance-v1.p.rapidapi.com")

    headers = {
    'x-rapidapi-host': "apidojo-yahoo-finance-v1.p.rapidapi.com",
    'x-rapidapi-key': key
    }

    conn.request("GET", "/auto-complete?region=US&q=tesla", headers=headers)

    res = conn.getresponse()
    data = res.read()
    return


def data_import(ticker, interval, timerange, key):
# Import data from Yahoo Finance
    
        url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/stock/v2/get-chart" # Making request to the Rakouten API 

        querystring = {"region":"US","interval":interval,"symbol":ticker,"range":timerange}

        headers = {
        'x-rapidapi-host': "apidojo-yahoo-finance-v1.p.rapidapi.com",
        'x-rapidapi-key': key
        }

        response = requests.request("GET", url, headers=headers, params=querystring) # Getting response
           
        rawData = response.json() # deconding data by means of the built-in solution JSON
        time = rawData["chart"]["result"][0]["timestamp"]

        for i in range(0,len(time),1):
            time[i] = datetime.fromtimestamp(time[i]).strftime("%Y-%m-%d %I:%M:%S") # Converting time from epoches to the readible format
            prices = rawData["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            localData = pd.DataFrame({
            "Data": time,
            "Price": prices
            })
            
        return(localData)

def get_chart(ticker, interval, timerange, finalData, key, update_prices = False):
# Get entries to the datebase, if update_prices = False then just recalculating revenues and stuff using the existing base
    
    if update_prices == False: # Do requests and update prices or use th eexisting db?
        index = finalData["Ticker"][finalData["Ticker"] == ticker].index[0] # Finding the number of the requested ticker
        localData = finalData["Price Data"].iloc[index]
        
    elif update_prices == True and ticker in finalData["Ticker"].values:
        print("The ticker has been already created")
        return(finalData)
    
    elif update_prices == True and ticker not in finalData["Ticker"].values:
         localData = data_import(ticker, interval, timerange, key)

        
    if check_if_closed(localData) == True: # if the company is closed, put it to the list and proceed
        f = open("closed.txt", "a")
        f.write(ticker)
        f.close()
        print("% has been closed" %ticker)
                        
    if localData["Price"].dropna()[0] > 12: # If the chart starts with the price higher than the entry threshold -> skip this company
        print("The price starts higher than the entry threshold")
        return(finalData)
        
    else:            
    
        try:
            start_date = localData[localData["Price"] > 12]["Data"].iloc[0] # Figuring out when the price movement began. For example, the day when the price got 11 bucks
            start_date_index = max(0, get_jump_date(localData))
            date_object = datetime.strptime(start_date, "%Y-%m-%d %I:%M:%S")
   
            pd.options.display.float_format = '{:,.2f}'.format
            finalData = finalData.append({"Ticker": ticker,
                             "Price Data": localData,
                             "IPO Date": get_ipo_date(localData).strftime('%B %d, %Y'),
                             "Price Jump Date": date_object.strftime('%B %d, %Y'),
                             "Days Till Jump": how_long(localData),
                             "Buy Price": "$%.2f" % get_av_buy_price(localData),
                             "1d Av. Rets, %": get_av_returns(localData, start_date_index, 1),
                             "3d Av. Rets, %": get_av_returns(localData, start_date_index, 3),
                             "1w Av. Rets, %": get_av_returns(localData, start_date_index, 7),
                             "1M Av. Rets, %": get_av_returns(localData, start_date_index, 30),
                             "Current Rets, %": get_current_returns(localData, start_date_index),
                            }, ignore_index = True)
        except Exception:
            finalData = finalData.append({"Ticker": ticker,
                             "Price Data": localData,
                             "IPO Date": get_ipo_date(localData).strftime('%B %d, %Y'),
                             "Price Jump Date": "Not Found",
                             "Days Till Jump": how_long(localData),
                             "1d Av. Rets, %": None,
                             "3d Av. Rets, %": None,                 
                             "1w Av. Rets, %": None,
                             "1M Av. Rets, %": None,
                             "Current Rets, %": None,
                            }, ignore_index = True)
        
    return(finalData)
    
def get_ipo_date(localData):

# Getting the IPO date as the first appearence on the stock market in the format of datetime object

    ipo_date = localData["Data"].iloc[0]
    ipo_date_dataobject = datetime.strptime(ipo_date, "%Y-%m-%d %I:%M:%S")
                                            
    return(ipo_date_dataobject)
                                            
def how_long(localData):

# How long did it take for the price to move

    jump_date = get_jump_date(localData, dateobject_format = True)
    
    if jump_date == None:
        return("No Jump")
    else:
        ipo_date = get_ipo_date(localData)
        delta = jump_date - ipo_date
        return(delta.days)
    

def get_jump_date(localData, dateobject_format = None):

# Getting the date of price jump. The "datetime" option is None if we need an index, is True when a datetime object
  
    if localData[localData["Price"] > 12]["Data"].shape[0] == 0: # Jump is when price got higher than 12
        return(None)
                                                                                    
    else:
    
        start_date = localData[localData["Price"] > 12]["Data"].iloc[0]
        start_date_dateobject = datetime.strptime(start_date, "%Y-%m-%d %I:%M:%S")
        start_date_text = start_date_dateobject.strftime('%Y-%m-%d')
        start_date_index = localData[localData["Data"].str.contains(start_date_text)].index[0]
        
        if dateobject_format == None:    
            return(start_date_index)
        else:
            return(start_date_dateobject)
    
def get_date_index(localData, start_date_index, plus_days = None): 
    if start_date_index == None:
        return(None)     
    else:
        start_date_dataobject = datetime.strptime(localData["Data"].iloc[start_date_index], "%Y-%m-%d %I:%M:%S")
        max_date = localData["Data"].iloc[-1]
        max_date_dataobject = datetime.strptime(max_date, "%Y-%m-%d %I:%M:%S")
        target_date_dataobject = start_date_dataobject + timedelta(days = plus_days)
        
        if  max_date_dataobject + timedelta(days = 0) < target_date_dataobject:
            return(None)
        else:   
        
     # The following error detector accounts for weekends or holidays and absence of data these days
    
            date_index = None
            i=0
            while date_index == None:
                try:
                    target_date_dataobject = start_date_dataobject + timedelta(days = plus_days+i)
                    i += 1
                    target_date_substring = target_date_dataobject.strftime('%Y-%m-%d')
                    if i == 0:
                        date_index = localData[localData["Data"].str.contains(target_date_substring)].index[-1]
                    else:
                        date_index = localData[localData["Data"].str.contains(target_date_substring)].index[0]
                        
                except IndexError:
                    pass
            return(date_index)

def plot_chart(ticker, finalData):
    
    index = finalData["Ticker"][finalData["Ticker"] == ticker].index[0] # Finding the number of the requested ticker
    ax = finalData["Price Data"].iloc[index].plot(x = "Data", y = "Price", figsize = (12,9))
    buy_price = get_av_buy_price(finalData["Price Data"].iloc[index])
    start_date_index = get_jump_date(finalData["Price Data"].iloc[index])                                     
    week_date_index = get_date_index(finalData["Price Data"].iloc[index], get_jump_date(finalData["Price Data"].iloc[index]), plus_days = 7)
    month_date_index = get_date_index(finalData["Price Data"].iloc[index], get_jump_date(finalData["Price Data"].iloc[index]), plus_days = 30)
    
    
    if buy_price == None:
        pass
    else:
        ax.axhline(buy_price, color = "red", ls="--")
                                            
    if start_date_index == None:
        pass
    else:
        ax.axvline(start_date_index, color = "black", ls="--")    
    
    if week_date_index == None:
        pass
    else:
        ax.axvline(week_date_index, color = "black", ls="--")

    if month_date_index == None:
        pass
    else:
        ax.axvline(month_date_index, color = "black", ls="--")
        
    ax.tick_params(axis='x', rotation=45)
    
    return ax

def get_returns(localData, start_date_index, period):
    
    target_date_index = get_date_index(localData, start_date_index, plus_days = period)
    
    if target_date_index == None:
        return(None)
    else:
# If the price just before the price jump is unknown than we take the average price obsrved before thsi timepoint
        if localData["Price"].iloc[start_date_index] > 0:
            rets = 100 * (localData["Price"].iloc[target_date_index]-localData["Price"].iloc[start_date_index])/localData["Price"].iloc[start_date_index]
        else:
            average = localData["Price"].iloc[:start_date_index].mean()
            rets = 100 * (localData["Price"].iloc[target_date_index]-average)/average
            
    return(rets)

def get_av_buy_price(localData):
# Average price before jump
    jump_date = get_jump_date(localData, dateobject_format = None)
    av_buy_price = localData["Price"][:jump_date].dropna().mean()
    if get_jump_date(localData, dateobject_format = None) == 0:
        av_buy_price = localData["Price"][jump_date]
    return(av_buy_price)

def get_av_returns(localData, start_date_index, period):
    
    '''
    Ouputs the average return if we would be a stock at start_date_index and sell every hour (change of index by 1) 
    '''
    
    start_date_index = get_jump_date(localData)
    target_date_index = get_date_index(localData, start_date_index, plus_days = period)
    av_buy_price = get_av_buy_price(localData)
    cum_rets = 0
    nan_number = 0
    if target_date_index == None:
        return(None)
    else:
         
        n = 0
        for i in range(start_date_index, target_date_index):
            n +=1
            if str(localData["Price"][start_date_index+n]) == "nan":
                nan_number += 1
                continue
            else:
                cum_rets += 100*(localData["Price"][start_date_index+n]-av_buy_price)/av_buy_price
        
        av_rets = cum_rets/(target_date_index-start_date_index-nan_number)
        return(av_rets)
    
    
    
def get_current_returns(localData, start_date_index):
    # If the price just before the price jump is unknown than we take the average price observed before this timepoint
    av_buy_price = get_av_buy_price(localData)   
    rets = 100 * (localData["Price"].dropna().iloc[-1]-av_buy_price)/av_buy_price
         
    return(rets)

def get_jump_price(localData, start_date_index):
    # If the price just before the price jump is unknown than we take the average price observed before this timepoint
    if start_date_index == None:
        return(None)
    else:
        if localData["Price"].iloc[start_date_index] > 0:
            price = localData["Price"].iloc[start_date_index]
        else:
            price = localData["Price"].iloc[:start_date_index].mean()
        return(price)
    
def check_if_closed(localData):

# Check if the company still exists
    last_date = localData["Data"].iloc[-1]
    last_date_dataobject = datetime.strptime(last_date, "%Y-%m-%d %I:%M:%S")
    today_dataobject = datetime.today()
    if last_date_dataobject + timedelta(days = 7) < today_dataobject:
        return(True)
    else:
        return(False)