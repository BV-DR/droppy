#!/usr/bin/env python
# -*- coding: latin_1 -*-

"""
  Time series function, using pandas DataFrame
"""

from __future__ import absolute_import, print_function
import numpy as np
import xarray as xa
import pandas as pd
from scipy import integrate
from scipy.interpolate import interp1d, UnivariateSpline
from math import pi, log
from matplotlib import pyplot as plt
from .. import pyplotTools


def scal_ramp(time, tStart, tEnd):
    time = time - tStart
    duration = tEnd - tStart
    if time > duration:
        return 1.
    else:
        return 10. * (time / duration)**3 - 15. * (time / duration)**4 + 6. * (time / duration)**5


ramp_v = np.vectorize(scal_ramp)


def rampDf(df, rStart, rEnd):
    """ Ramp the signal between rStart and rEnd (in place) """
    a = ramp_v(df.index[:], rStart, rEnd)
    for c in df.columns:
        df[c][:] *= a[:]
    return df


def fillCos(A=1.0, T=10., tMin=0., tMax=50., n=200):
    """ for testing purpose, fill signal with a cosine """
    xAxis = np.linspace(tMin, tMax, n)
    data = np.zeros((n, 2))
    data[:, 0] = A * np.cos(2 * pi * xAxis / T)
    data[:, 1] = A * np.sin(2 * pi * xAxis / T)
    return pd.DataFrame(data=data, index=xAxis, columns=["Cos", "Sin"])


def reSample(df, dt=None, xAxis=None, n=None, kind='linear', extrapolate=False,extrap_value=0.0):
    """re-sample the signal
    """

    if type(df) == pd.Series:
        df = pd.DataFrame(df)

    f = interp1d(df.index, np.transpose(df.values), kind=kind, axis=-1, copy=True, bounds_error=(not extrapolate), fill_value=extrap_value, assume_sorted=True)
    if dt:
        end = int(+(df.index[-1] - df.index[0]) / dt) * dt + df.index[0]
        xAxis = np.linspace(df.index[0], end, 1 + int(+(end - df.index[0]) / dt))
    elif n:
        xAxis = np.linspace(df.index[0],  df.index[-1], n)
    elif xAxis is None:
        raise(Exception("reSample : either dt or xAxis should be provided"))

    # For rounding issue, ensure that xAxis is within ts.xAxis
    #xAxis[ np.where( xAxis > np.max(df.index[:]) ) ] = df.index[ np.where( xAxis > np.max(df.index[:]) ) ]
    return pd.DataFrame(data=np.transpose(f(xAxis)), index=xAxis, columns=df.columns)


def dx(df):
    return (df.index[-1] - df.index[0]) / (len(df) - 1)


def slidingFFT(se, T,  n=1, tStart=None, preSample=False, nHarmo=5, kind=abs, phase=None):
    """
    Harmonic analysis on a sliding windows
    se : Series to analyse
    T : Period
    tStart : start _xAxis
    n : size of the sliding windows in period.
    reSample : reSample the signal so that a period correspond to a integer number of time step
    nHarmo : number of harmonics to return
    kind : module, real,  imaginary part, as a function (abs, np.imag, np.real ...)
    phase : phase shift (for instance to extract in-phase with cos or sin)
    """

    if (type(se) == pd.DataFrame):
        if len(se.columns) == 1:
            se = se.iloc[:, 0]

    nWin = int(0.5 + n * T / dx(se))
    # ReSample to get round number of time step per period
    if preSample:
        new = reSample(se, dt=n * T / (nWin))
    else:
        new = se
    signal = new.values[:]
    # Allocate results
    res = np.zeros((new.shape[0], nHarmo))
    for iWin in range(new.shape[0] - nWin):
        sig = signal[iWin: iWin + nWin]  # windows
        fft = np.fft.fft(sig)  # FTT
        if phase is not None:                 # Phase shift
            fft *= np.exp(1j * (2 * pi * (iWin * 1. / nWin) + phase))
        fftp = kind(fft)  # Take module, real or imaginary part
        spectre = 2 * fftp / (nWin)  # Scale
        for ih in range(nHarmo):
            res[iWin, ih] = spectre[ih * n]
            if ih == 0:
                res[iWin, ih] /= 2.0
            #if ih == 0 : res[iWin, ih] = 2.0
    return pd.DataFrame(data=res, index=new.index, columns=map(lambda x: "Harmo {:} ({:})".format(x, se.name), range(nHarmo)))


def getPSD(df, dw=0.05, roverlap=0.5, window='hanning', detrend='constant', unit="rad"):
    """
       Compute the power spectral density
    """
    from scipy.signal import welch

    if type(df) == pd.Series:
        df = pd.DataFrame(df)

    nfft = int((2 * pi / dw) / dx(df))
    nperseg = 2**int(log(nfft) / log(2))
    noverlap = nperseg * roverlap

    """ Return the PSD of a time signal """
    data = []
    for iSig in range(df.shape[1]):
        test = welch(df.values[:, iSig], fs=1. / dx(df), window=window, nperseg=nperseg, noverlap=noverlap, nfft=nfft, detrend=detrend, return_onesided=True, scaling='density')
        data.append(test[1] / (2 * pi))
    if unit in ["Hz", "hz"]:
        xAxis = test[0][:]
    else:
        xAxis = test[0][:] * 2 * pi
    return pd.DataFrame(data=np.transpose(data), index=xAxis, columns=["psd(" + str(x) + ")" for x in df.columns])


def getCSD(df, dw=0.05, roverlap=0.5, window='hanning', detrend='constant', unit="rad"):
    """
       Compute the cross-spectral density
    """
    from scipy.signal import csd

    nfft = int((2 * pi / dw) / dx(df))
    nperseg = 2**int(log(nfft) / log(2))
    noverlap = nperseg * roverlap

    """ Return the PSD of a time signal """
    data = []
    for iSig in range(df.shape[1]):
        test = csd(df.values[:, 0], df.values[:, 1], fs=1. / dx(df), window=window, nperseg=nperseg, noverlap=noverlap, nfft=nfft, detrend=detrend, return_onesided=True, scaling='density')
        data.append(test[1] / (2 * pi))
    if unit in ["Hz", "hz"]:
        xAxis = test[0][:]
    else:
        xAxis = test[0][:] * 2 * pi
    return pd.DataFrame(data=np.transpose(data), index=xAxis, columns=["csd1", "csd2"])



def getRAO( df, cols=None, *args, **kwargs ):
    """Return RAO from wave elevation and response signal

    Use Welch method to return RAO (amplitudes and phases)

       df = dataframe containing wave elevation and response
       cols (tuple) : indicate labels of elevation and response
       *args, **kwargs : passed to getPSD method
    """

    if cols is None :
        df_ = df.iloc[ :, [0,1] ]
    else :
        df_ = df.loc[ :, cols ]

    #Power Spectral Density
    psd = getPSD( df_, *args, **kwargs )

    #Cross Spectral Density
    csd = getCSD( df_, *args, **kwargs )

    return pd.DataFrame( index = psd.index, data = { "amp" : (psd.iloc[:,1] / psd.iloc[:,0])**0.5 ,
                                                     "phase" : np.angle(csd.iloc[:,0]) } )



def fftDf(df, part=None, index="Hz"):
    # Handle series or DataFrame
    if type(df) == pd.Series:
        df = pd.DataFrame(df)
        ise = True
    else:
        ise = False
    res = pd.DataFrame(index=np.fft.rfftfreq(df.index.size, d=dx(df)))
    for col in df.columns:
        res[col] = np.fft.rfft(df[col])
        if part is not None:
            res[col] = part(res[col])

    res /= (0.5 * df.index.size)
    res.loc[0, :] *= 0.5

    if index == "Hz":
        pass
    elif "rad" in index.lower():
        res.index *= 2 * np.pi

    if ise:
        return res.iloc[:, 0]
    else:
        return res


def bandPass(df, fmin=None, fmax=None, unit="Hz"):
    """
       Return filtered signal
    """
    from scipy.fftpack import rfft, irfft, rfftfreq  # Warning convention of scipy.fftpack != numpy.fft   !!!
    if unit in ["rad", "rad/s", "Rad", "Rad/s"]:
        if fmin is not None:
            fmin = fmin / (2 * pi)
        if fmax is not None:
            fmax = fmax / (2 * pi)

    if type(df) == pd.Series:
        df = pd.DataFrame(df)
        ise = True
    else:
        ise = False
    filtered = pd.DataFrame(index=df.index)
    W = rfftfreq(df.index.size, d=dx(df))
    for col in df.columns:
        tmp = rfft(df[col])
        if fmin is not None:
            tmp[(W < fmin)] = 0
        if fmax is not None:
            tmp[(W > fmax)] = 0
        filtered[col] = irfft(tmp)
    if ise:
        return filtered.iloc[:, 0]
    else:
        return filtered


def derivFFT(df, n=1):
    """ Deriv a signal trought FFT, warning, edge can be a bit noisy...
    indexList : channel to derive
    n : order of derivation
    """
    deriv = []
    for iSig in range(df.shape[1]):
        fft = np.fft.fft(df.values[:, iSig])  # FFT
        freq = np.fft.fftfreq(df.shape[0], dx(df))

        from copy import deepcopy
        fft0 = deepcopy(fft)
        if n > 0:
            fft *= (1j * 2 * pi * freq[:])**n  # Derivation in frequency domain
        else:
            fft[-n:] *= (1j * 2 * pi * freq[-n:])**n
            fft[0:-n] = 0.

        tts = np.real(np.fft.ifft(fft))
        tts -= tts[0]
        deriv.append(tts)  # Inverse FFT

    return pd.DataFrame(data=np.transpose(deriv), index=df.index, columns=["DerivFFT(" + x + ")" for x in df.columns])

def deriv(df, n=1, axis=None):
    """ Deriv a signal through finite difference
    """
    # Handle series, DataFrame or DataArray
    if type(df)==pd.core.frame.DataFrame:
        deriv = pd.DataFrame(index=df.index, columns=df.columns)
    elif type(df)==pd.core.series.Series:
        deriv = pd.Series(index=df.index)
    elif type(df)==xa.core.dataarray.DataArray:
        deriv = xa.DataArray(coords=df.coords,dims=df.dims,data=np.empty(df.shape))
    else:
        raise(Exception('ERROR: input type not handeled, please use pandas Series or DataFrame'))

    #compute first derivative
    if n == 1:
        if type(df)==pd.core.frame.DataFrame:
            for col in df.columns:
                deriv.loc[:,col] = np.gradient(df[col],df.index)
        elif type(df)==pd.core.series.Series:
            deriv[:] = np.gradient(df,df.index)
        elif type(df)==xa.core.dataarray.DataArray:
            if axis==None: raise(Exception('ERROR: axis should be specifed if using DataArray'))
            deriv.data = np.gradient(df,df.coords[df.dims[axis]].values,axis=axis)
    else:
        raise(Exception('ERROR: 2nd derivative not implemented yet'))

    return deriv

def integ(df, n=1, axis=None, origin=None):
    """ Integrate a signal with trapeze method
    """
    # Handle series, DataFrame or DataArray
    if type(df)==pd.core.frame.DataFrame:
        integ = pd.DataFrame(index=df.index, columns=df.columns)
        if origin==None: origin=[0.]*df.shape[1]
    elif type(df)==pd.core.series.Series:
        integ = pd.Series(index=df.index)
        if origin==None: origin=0.
    elif type(df)==xa.core.dataarray.DataArray:
        integ = xa.DataArray(coords=df.coords,dims=df.dims,data=np.empty(df.shape))
    else:
        raise(Exception('ERROR: input type not handeled, please use pandas Series or DataFrame'))
        
    #compute first integral
    if n == 1:
        if type(df)==pd.core.frame.DataFrame:
            for i, col in enumerate(df.columns):
                integ.loc[:,col] = integrate.cumtrapz(df[col], df.index, initial=0) + origin[i]
        elif type(df)==pd.core.series.Series:
            integ[:] = integrate.cumtrapz(df, df.index, initial=0) + origin
        elif type(df)==xa.core.dataarray.DataArray:
            if axis==None: raise(Exception('ERROR: axis should be specifed if using DataArray'))
            integ.data = integrate.cumtrapz(df, df.coords[df.dims[axis]].values,axis=axis, initial=0)
    else:
        raise(Exception('ERROR: 2nd integral not implemented yet'))
            
    return integ

def smooth(df, k=3, axis=None, inplace=False):
    """ Smooth a signal using scipy.interpolate.UnivariateSpine of order k
    """
    # Handle series, DataFrame or DataArray
    if type(df)==pd.core.frame.DataFrame:
        smooth = pd.DataFrame(index=df.index, columns=df.columns)
    elif type(df)==pd.core.series.Series:
        smooth = pd.Series(index=df.index)
    elif type(df)==xa.core.dataarray.DataArray:
        smooth = xa.DataArray(coords=df.coords,dims=df.dims,data=np.empty(df.shape))
    else:
        raise(Exception('ERROR: input type not handeled, please use pandas Series or DataFrame'))

    #smooth using spline
    if type(df)==pd.core.frame.DataFrame:
        for col in df.columns:
            spl = UnivariateSpline(df.index,df[col],k=k)
            smooth.loc[:,col] = spl(df.index)
    elif type(df)==pd.core.series.Series:
        spl = UnivariateSpline(df.index,df.values,k=k)
        smooth[:] = spl(df.index)
    elif type(df)==xa.core.dataarray.DataArray:
        raise(NotImplementedError)
#        if axis==None: raise(Exception('ERROR: axis should be specifed if using DataArray'))
#        deriv.data = np.gradient(df,df.coords[df.dims[axis]].values,axis=axis)
    else:
        raise(Exception('ERROR: 2nd derivative not implemented yet'))

    return smooth

def testDeriv(display):
    ts = read(r'../../testData/motion.dat')
    tsd = derivFFT(ts,  n=2)
    ts2 = deriv(ts,  n=2)
    if display:
        comparePlot([ts, tsd, ts2], 3)


def testPSD(display=True):
    """ Read a signal, compute PSD and compare standard deviation to m0 """
    df = read(r'../../testData/motion.dat')

    RsSig = np.std(df.values[:, 0]) * 4
    print("Rs from sigma ", RsSig)
    psd = getPSD(df)
    RsM0 = (np.sum(psd.values[:, 0]) * dx(psd)) ** 0.5 * 4.004
    print("Rs from m0    ", RsM0)

    psd = psd[0.1: 2.0]
    if display:
        df.plot()
        psd.plot()
        plt.show()


def testSlidingFFT(display=True):
    tsCos = fillCos(T=10.)
    tsCos2 = fillCos(A=0.5,  T=5, tMin=0, tMax=50, n=200)
    tsSum = tsCos + tsCos2
    tsSum += 1.
    tsSum.plot()
    plt.show()
    tsSum = rampDf(tsSum,  0, 10)
    tsSum.plot()
    plt.show()

    sFFT = slidingFFT(tsSum,  T=10., n=1,  preSample=True, kind=np.abs)

    if display:
        tsSum.plot()
        sFFT.plot()
        plt.show()


def comparePlot(listDf, index=0, display=True, labels=None, title=None, xlabel=None, ylabel=None):
    fig = plt.figure()
    axe = fig.add_subplot(111)
    axe.grid(True)

    if title is not None:
        axe.set_title(title)
    if xlabel is not None:
        axe.set_xlabel(xlabel)
    if ylabel is not None:
        axe.set_ylabel(ylabel)

    marker = pyplotTools.newMarkerIterator()

    for i, ic in enumerate(listDf):
        if labels is None:
            l_ = ic.columns[index]
        else:
            l_ = labels[i]
        axe.plot(ic.index[:], ic.values[:, index], label=l_, marker=marker.next())
    axe.legend()
    if display:
        plt.show()
    return fig, axe


def testOperation():
    tsOf = read(r'../../testData/motion.dat')
    # print tsOf.values[5,5]

    totOf = pd.DataFrame()
    totOf["New"] = tsOf["Surge"] + tsOf["Sway"]

    totOf.plot()
    plt.show()

    # print tot.magnitude[55] , ts.magnitude[55,2] + ts.magnitude[55,3]*4
    return


def testFFT(display=True):
    tsCos = fillCos(A=1.0, T=10., tMin=0, tMax=100, n=1000)
    tsCos2 = fillCos(A=0.5,  T=5., tMin=0, tMax=100, n=1000)
    tsCos3 = fillCos(A=0.5,  T=2., tMin=0, tMax=100, n=1000)
    tsSum = tsCos + tsCos2 + tsCos3
    tsSum = tsSum.iloc[:, 0]
    tsSum.name = "Sum"

    df = fftDf(tsSum)
    df.plot()
    if display:
        plt.show()


def testBandPass(display=True):
    tsCos = fillCos(A=1.0, T=10., tMin=0, tMax=100, n=1000)
    tsCos2 = fillCos(A=0.5,  T=5., tMin=0, tMax=100, n=1000)
    tsCos3 = fillCos(A=0.5,  T=2., tMin=0, tMax=100, n=1000)
    tsSum = tsCos + tsCos2 + tsCos3
    tsSum = tsSum.iloc[:, 0]
    tsSum.name = "Sum"
    tsCos3 = tsCos3.iloc[:, 0]
    tsCos3.name = "T=2"
    tsCos2 = tsCos2.iloc[:, 0]
    tsCos2.name = "T=5"
    tsCos = tsCos.iloc[:, 0]
    tsCos.name = "T=10"
    filtered = bandPass(tsSum, fmin=1. / 5.1,  fmax=1. / 4.9)
    filtered.name = "filtered"
    ax = tsSum.plot()
    filtered.plot(ax=ax, linestyle="", marker="o")
    tsCos2.plot(ax=ax)
    tsCos.plot(ax=ax)
    tsCos3.plot(ax=ax)
    ax.legend()
    ax.set_xlim([50, 60])
    if display:
        plt.show()


def getRMS(df):
    rms = np.sqrt(df.mean()**2 + df.std()**2)
    return rms

def getAutoCorrelation( se ):
    """To check
    """
    x = se.values
    xp = x - x.mean()
    result = np.correlate(xp, xp, mode='full')
    result = result[result.size // 2:]
    return pd.Series( index = np.arange( se.index[0]-se.index[0], len(result)*dx(se) ,  dx(se) ) , data = result / np.var(x) / len(x) )


if __name__ == '__main__':

    # Launch the test
    display = True

    testFFT(display)
    # testBandPass()
    #a = read( r"D:\Support\Igor\KCS\TDS\KCS125936\real_001\RK4__NL\motion.dat")


#   testPSD(display)
#   testDeriv(display)
#   testSlidingFFT(display)
#    testOperation()

#   display = True

    print("Done")
