from flask import Flask, render_template, request, send_file, make_response
app = Flask(__name__)

import pandas as pd
#import numpy as np
import time
import matplotlib.pyplot as plt
import numpy as np
import datetime
from io import BytesIO
import random

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter

df = pd.read_csv("BE.csv", sep=",")  

def backtest(df, lags, cutoff, initValue, tilt):

    df = df.reset_index(drop=True)
    Price = df.Close
    Tc = df.Tc
    print('lags: ', type(lags))
    print('cutoff: ', type(cutoff))
    print('initValue:', type(initValue))
    print('tilt:', type(tilt))
    print(Price.rolling(lags, min_periods=1).mean())
    MAdev = Price/Price.rolling(lags, min_periods=1).mean() - 1
    print(MAdev)
    t0 = time.clock()
    cValue = initValue
    aBase = 0.5*cValue
    aQuote = 0.5*cValue/Price[0]
    print(aBase)

    Value = [cValue]
    Position = [0]
    Tt = [Tc[0]]
    print(Tt)
    for i in range(lags,len(Tc),lags):        
        cValue = aBase*1 + aQuote*Price[i]    
        wBase = 0.5
        if (MAdev[i] > cutoff):             cPos = -1
        elif (MAdev[i] < -cutoff):          cPos = 1
        else: cPos = 0
        
        wBase = 0.5 + cPos*tilt
        aBase = wBase*cValue
        aQuote = (1-wBase)*cValue/Price[i] 
        Value.append(cValue)
        Position.append(cPos)
        Tt.append(Tc[i])
    
    t1 = time.clock()
    Return = np.diff(np.log(Value))
    SR = np.mean(Return)/np.std(Return)*np.sqrt(60*24*365/lags)
    
    print('sma interval = %d, cutoff = %g, starting value = %g, tilt = %g' %(lags, cutoff, 1, tilt))
    print('final base amount = %g, final quote amount = %g' %(aBase,aQuote))
    print('final value = %g, Sharpe Ratio = %g' %(cValue,SR))
    print('number of buys = %d, number of sells = %d' %(Position.count(1), Position.count(-1)))
    timeBT = t1-t0
    print('Backtest time: %g' % (timeBT))  
    print('  ')    
    fig = plt.figure(figsize=(10,6))
    ax = fig.add_subplot(221); ax.plot(Tc,MAdev); ax.grid();  ax.set_title('MAdev');
    ax.axhline(y=cutoff,c="red",linewidth=0.5,zorder=0)
    ax.axhline(y=-cutoff,c="red",linewidth=0.5,zorder=0)
    ax = fig.add_subplot(222); ax.plot(Tc,Price); ax.grid();  ax.set_title('Price');
    ax = fig.add_subplot(223); ax.plot(Tt,Value); ax.grid();  ax.set_title('Value');
    ax = fig.add_subplot(224); ax.plot(Tt,Position,'.');   ax.grid();  ax.set_title('Buys and Sells'); 
    #return (aBase, aQuote, cValue, Position.count(1), Position.count(-1), SR)
    return [aBase, aQuote, cValue, SR, Position.count(1), Position.count(-1), timeBT, fig]


@app.route("/")
def inputPage():
    return render_template('submit_form.html')

@app.route("/graphs")
def images():
    initValue = int(request.args.get('start'))
    lags = int(request.args.get('length'))
    cutoff = float(request.args.get('cutoff'))
    tilt = float(request.args.get('tilt'))
    print(initValue, lags, cutoff, tilt)
    print(df)
    results = backtest(df[100:], lags, cutoff, initValue, tilt )
    image = results[7]
    canvas=FigureCanvas(image)
    png_output = BytesIO()
    canvas.print_png(png_output)
    response=make_response(png_output.getvalue())
    response.headers['Content-Type'] = 'image/png'
    return response   

@app.route('/', methods = ['POST'])
def results():
    if (len(request.form['start'])==0 or len(request.form['length'])==0 or len(request.form['cutoff'])==0 or len(request.form['tilt'])==0):
        return render_template('error.html', message = "One or more input fields is empty")
    initValue = int(request.form['start'])
    lags = int(request.form['length'])
    cutoff = float(request.form['cutoff'])
    tilt = float(request.form['tilt'])
    if (initValue<=0):
        return render_template('error.html', message = "Starting Capital Amount must be greater than 0")
    if (lags<=0):
        return render_template('error.html', message = "SMA Length must be greater than 0 minutes")
    if (cutoff<=0 or cutoff >= 1.0):
        return render_template('error.html', message = "Percentage Cutoff must be between 0.00-1.00")
    if (tilt<=0 or tilt >= 1.0):
        return render_template('error.html', message = "Tilt must be between 0.00-1.00")
    print(initValue, lags, cutoff, tilt)
    print(df)
    results = backtest(df[100:], lags, cutoff, initValue, tilt )
    fba = results[0]
    fqa = results[1]
    fv = results[2]
    SR = results[3]
    nB = results[4]
    nS = results[5]
    btT = results[6]
    return render_template('results.html', initValue = initValue, lags = lags, cutoff = cutoff, tilt = tilt, fba = "%0.4f" % fba, fqa = "%0.4f" % fqa, fv = "%0.4f" % fv, SR = "%0.4f" % SR, nB = nB, nS = nS, btT = "%0.4f" % btT)

#https://stackoverflow.com/questions/20107414/passing-a-matplotlib-figure-to-html-flask
    