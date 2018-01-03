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

def backtest(df, lags, cutoff, initValue, tilt, momentum):
    df = df.reset_index(drop=True)
    Price = df.Close
    Tc = df.Tc
    MAD = Price/Price.rolling(lags, min_periods=1).mean() - 1
    t0 = time.clock()
    Nc = len(Tc)
    
    MADt = np.array(MAD[lags:Nc:lags]) 
    Pricet = np.array(Price[lags:Nc:lags]) 
    Tt = np.array(Tc[lags:Nc:lags]) 
    Nt = len(Tt)     
    Value = initValue + np.zeros(Nt)
    ValueEW = initValue + np.zeros(Nt)
    Position = np.zeros(Nt) 
    for i in range(1,Nt):   
        wBase = 0.5 - Position[i-1]*tilt
        wQuote = 1 - wBase
        Value[i] = Value[i-1]*(wBase*1 + wQuote*Pricet[i]/Pricet[i-1])    
        ValueEW[i] = ValueEW[i-1]*(0.5*1 + 0.5*Pricet[i]/Pricet[i-1])          
        
        # Rebalancing
        if (MADt[i] > cutoff):             cPos = 1
        elif (MADt[i] < -cutoff):          cPos = -1
        else: cPos = 0  
        Position[i] = cPos*momentum              
    
    # print results
    t1 = time.clock()
    FinalValue = Value[-1]
    SR = SharpeRatio(Value,lags)
    res = [FinalValue,SR,FinalValue*0.5,FinalValue*0.5/Pricet[-1],(Position==1).sum(), (Position==-1).sum()]
    FinalValueEW = ValueEW[-1]
    SREW = SharpeRatio(ValueEW,lags)  
    resEW = [FinalValueEW,SREW,FinalValueEW*0.5,FinalValueEW*0.5/Pricet[-1]]   
    baseMT = res[2]
    quoteMT = res[3]
    baseEW = resEW[2]
    quoteEW = resEW[3]
    nB = res[4]
    nS = res[5]
    timeBT = (t1-t0)
          
    print('Parameters: Frequency = %d min, cutoff = %g, starting value = %g, tilt = %g' %(lags, cutoff, 1, tilt))
    #print('final base amount = %g, final quote amount = %g' %(aBase,aQuote))
    print('MT: Final Value = %.2f, Sharpe Ratio = %.2f, Base Amount = %.2f, Quote Amount = %.2f' %(res[0],res[1],res[2],res[3]))
    print('EW: Final Value = %.2f, Sharpe Ratio = %.2f, Base Amount = %.2f, Quote Amount = %.2f' %(resEW[0],resEW[1],resEW[2],resEW[3]))
    print('Number of buys = %d, number of sells = %d' %(res[4],res[5]))
    print('Backtest time: %.3f sec' % (t1-t0))  
    print('  ')    
        
    # plot results
    fig = plt.figure(figsize=(10,6))    
    ax = fig.add_subplot(221); ax.plot(Tc,Price/Price[0]); ax.grid();  
    ax.set_title('Currency Cumulative Return');    
    ax = fig.add_subplot(222); ax.plot(Tt,MADt); ax.grid();  
    ax.set_title('Price-to-SMA deviation');
    ax.axhline(y=cutoff,c='r',zorder=0);     ax.axhline(y=-cutoff,c='r',zorder=0)    
    ax = fig.add_subplot(223); 
    ax.plot(Tt,Value*0+1,label='BH'); 
    ax.plot(Tt,ValueEW,label='EW'); 
    ax.plot(Tt,Value,label='MT'); 
    ax.grid();  ax.set_title('Account Value');      plt.legend()    
    ax = fig.add_subplot(224)        
    weightQuote = 0.5 + Position*tilt       
    ax.plot(Tt,weightQuote,'.');   
    ax.grid();   ax.set_title('Weight in Quote');    plt.legend()    
    #return (Value[-1], (Position==1).sum(), (Position==-1).sum(), SR, SREW) 
    #return (aBase, aQuote, cValue, Position.count(1), Position.count(-1), SR)
    
    #res = [FinalValue,SR,FinalValue*0.5,FinalValue*0.5/Pricet[-1],(Position==1).sum(), (Position==-1).sum()]
    #resEW = [FinalValueEW,SREW,FinalValueEW*0.5,FinalValueEW*0.5/Pricet[-1]] 
    
    return [FinalValueEW, SREW, FinalValue, SR, nB, nS, timeBT, baseMT, quoteMT, baseEW, quoteEW, fig]

def SharpeRatio(Value,lags):
    Return = np.diff(np.log(Value))
    return np.mean(Return)/np.std(Return)*np.sqrt(60*24*365/lags)

@app.route("/about")
def about():
    return render_template('about.html')

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
    print("notstring-type ", type(request.args.get('stratype')))
    print("nonstring request ", request.args.get('stratype'))
    print("str - type ", type(str(request.args.get('stratype'))))
    print("str - request ", str(request.args.get('stratype')))
    stratype = request.args.get('stratype')
    if (stratype=='Momentum'):
        momentum = 1
    if (stratype=='Contrarian'):
        momentum = -1
    print(momentum)
    results = backtest(df[100:], lags*60, cutoff/100, initValue, tilt/100, momentum)
    image = results[11]
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
    print('Strategy type: ', str(request.form['stratype']))
    stratype = str(request.form['stratype'])
    if (stratype=='Momentum'):
        momentum = 1
    if (stratype=='Contrarian'):
        momentum = -1
    if (initValue<=0):
        return render_template('error.html', message = "Starting Capital Amount must be greater than 0")
    if (lags<=0):
        return render_template('error.html', message = "SMA Length must be greater than 0 minutes")
    if (cutoff<=0 or cutoff >= 100):
        return render_template('error.html', message = "Percentage Cutoff must be between 0-100")
    if (tilt<=0 or tilt > 50):
        return render_template('error.html', message = "Percent Exchanged must be between 0-50")
    print(initValue, lags, cutoff, tilt)
    results = backtest(df[100:], lags*60, cutoff/100, initValue, tilt/100, momentum)
    #return [fvEW, SREW, fv, SR, nB, nS, timeBT, fig]
    fvEW = results[0]
    SREW = results[1]
    fv = results[2]
    SR = results[3]
    nB = results[4]
    nS = results[5]
    btT = results[6]
    baseMT = results[7]
    quoteMT = results[8]
    baseEW = results[9]
    quoteEW = results[10]
    return render_template('results.html', stratype = stratype, initValue = initValue, lags = lags, cutoff = cutoff, tilt = tilt, fv = "%0.2f" % fv, SR = "%0.3f" % SR, nB = nB, nS = nS, fvEW = "%0.3f" %  fvEW, srEW = "%0.3f" % SREW, btT = "%0.3f" % btT, baseMT = "%0.3f" % baseMT, quoteMT = "%0.3f" % quoteMT, baseEW = "%0.3f" % baseEW, quoteEW = "%0.3f" % quoteEW)

#https://stackoverflow.com/questions/20107414/passing-a-matplotlib-figure-to-html-flask
    