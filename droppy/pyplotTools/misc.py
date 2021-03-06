import itertools
import numpy as np

colorCycle = ('b', 'r', 'c' , 'm', 'y' , 'k', 'g')
def newColorIterator(ccycle=None,cmap=None,n=10,bounds=[0,1]):
    if ccycle is not None:
        if hasattr(ccycle,'__len__'): clrCycle = ccycle
        else: print('Not Implemented')
        
    elif cmap is not None:
        import matplotlib.cm as cm
        colorMap = cm.get_cmap(cmap)
        clrCycle = (colorMap(i) for i in np.linspace(bounds[0],bounds[1],n))
    else:
        clrCycle = colorCycle
    return itertools.cycle(clrCycle)


markerCycle = ('o', 'v', "s", '*' , 'D', "+" , "x")
def newMarkerIterator(mcycle=None):
    if mcycle is not None:
        if hasattr(mcycle,'__len__'): mkrCycle = mcycle
        else: print('Not Implemented')
    else:
        mkrCycle = markerCycle
    return itertools.cycle(mkrCycle)


linestyleCycle = ('-', '--', '-.', ':')
def newLinestyleIterator(lcycle=None):
    if lcycle is not None:
        if hasattr(lcycle,'__len__'): lstCycle = lcycle
        else: print('Not Implemented')
    else:
        lstCycle = linestyleCycle
    return itertools.cycle(lstCycle)


def getAngleColorMappable( unit = "rad", cmap = "twilight" ):
    if "rad" in unit.lower() :
        vmax = 2*np.pi
    else :
        vmax = 360.
    return getColorMappable( vmin = 0.0 , vmax = vmax , cmap = cmap )


def getColorMappable( vmin, vmax, cmap = "viridis" ):
    import matplotlib.colors as colors
    import matplotlib.cm as cm
    cNorm  = colors.Normalize( vmin=vmin, vmax=vmax)
    scalarMap = cm.ScalarMappable(norm=cNorm, cmap=cmap)
    return scalarMap


def pyplotLegend(plt=None,ax=None):
    if plt is not None :
        ax = plt.get_axes()[0]
    handles, labels =  ax.get_legend_handles_labels()
    uniqueLabels = sorted(list(set(labels )))
    uniqueHandles = [handles[labels.index(l)] for l in uniqueLabels ]
    return uniqueHandles, uniqueLabels


def uniqueLegend(ax, *args, **kwargs) :
    ax.legend( *pyplotLegend(ax=ax), *args, **kwargs )


def autoscale_xy(ax,axis='y',margin=0.1):
    """This function rescales the x-axis or y-axis based on the data that is visible on the other axis.
    ax -- a matplotlib axes object
    axis -- axis to rescale ('x' or 'y')
    margin -- the fraction of the total height of the y-data to pad the upper and lower ylims"""

    import numpy as np

    def get_boundaries(xd,yd,axis):
        if axis == 'x':
            bmin,bmax = ax.get_ylim()
            displayed = xd[((yd > bmin) & (yd < bmax))]
        elif axis == 'y':
            bmin,bmax = ax.get_xlim()
            displayed = yd[((xd > bmin) & (xd < bmax))]
        h = np.max(displayed) - np.min(displayed)
        cmin = np.min(displayed)-margin*h
        cmax = np.max(displayed)+margin*h
        return cmin,cmax

    cmin,cmax = np.inf, -np.inf

    #For lines
    for line in ax.get_lines():
        xd = line.get_xdata(orig=False)
        yd = line.get_ydata(orig=False)
        new_min, new_max = get_boundaries(xd,yd,axis=axis)
        if new_min < cmin: cmin = new_min
        if new_max > cmax: cmax = new_max

    #For other collection (scatter)
    for col in ax.collections:
        xd = col.get_offsets().data[:,0]
        yd = col.get_offsets().data[:,1]
        new_min, new_max = get_boundaries(xd,yd,axis=axis)
        if new_min < cmin: cmin = new_min
        if new_max > cmax: cmax = new_max

    if   axis=='x': ax.set_xlim(cmin,cmax)
    elif axis=='y': ax.set_ylim(cmin,cmax)

    
def rgb_to_hexa( r, g, b ) :
    return f"#{r:02x}{g:02x}{b:02x}"

def hexa_to_rgb( hexcode ) :
    return tuple(map(ord,hexcode[1:].decode('hex')))

def negativeColor( r,g,b ):
    if max( np.array([r,g,b]) > 1. ) : 
       return 255-r , 255-g, 255-b
    else :
       return 1. - r , 1.-g, 1.-b

