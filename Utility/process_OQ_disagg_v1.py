def process_OQ_disagg(Mbin,dbin,path_disagg_results,output_filename='disagg_results.pkl'):
    """
    Details:
    Process the disaggregation ouputs from OpenQuake
    This script will take the disaggregation results and report back the mean
    magnitude and distance pair for each site

    Information:
    Author: Gerard J. O'Reilly
    First Version: April 2020

    Notes:

    References:

    Inputs:
    Mbin: Magnitude bin width
    dbin: Distance bin width
    path_disagg_results: Path to the disaggregation results
    output_filename: Save outputs to a pickle file (optional)

    Returns:
    lon: Longitude
    lat: Latitude
    im: Intensity measure
    Tr: Return period
    M: Magnitude
    R: Distance
    apoe_norm: Annual probability of exceedance, H
    modeLst: List of the modal disaggregation results
    meanLst: List of the mean disaggregation results

    """

    lat = []
    lon = []
    modeLst, meanLst = [],[]
    im = []
    poe = []
    Tr =[]
    apoe_norm = []
    M, R = [], []

    import os
    import pandas as pd
    import numpy as np
    import pickle
    import math

    for file in os.listdir(path_disagg_results):
        if file.startswith('rlz') and file.find('Mag_Dist')>0 and file.find('Mag_Dist_Eps')<0:
            # Load the dataframe
            df=pd.read_csv(''.join([path_disagg_results,'/',file]),skiprows=1)

            # Strip the IM out of the file name
            im.append(file.rsplit('-')[2])

            # Get some salient values
            f = open(''.join([path_disagg_results,'/',file]), "r")
            ff=f.readline().split(',')
            inv_t = float(ff[8].replace(" investigation_time=",""))
            lon.append(float(ff[9].replace(" lon=","")))
            lat.append(float(ff[10].replace(" lat=","")))
            poe.append(float(ff[11].replace(" poe=","").replace("'","")))
            Tr.append(-inv_t/np.log(1-poe[-1]))

            # Extract the poe and annualise
            df['apoe'] = -np.log(1-df['poe'])/inv_t

            # Normalise the apoe for disaggregation plotting
            df['apoe_norm'] = df['apoe']/ df['apoe'].sum()
            apoe_norm.append(df['apoe_norm'])

            # Compute the modal value (highest apoe)
            mode=df.sort_values(by='apoe_norm',ascending=False)[0:1]
            modeLst.append([mode['mag'].values[0],mode['dist'].values[0]])

            # Compute the mean value
            meanLst.append([np.sum(df['mag']*df['apoe_norm']), np.sum(df['dist']*df['apoe_norm'])])

            # Report the individual mangnitude and distance bins
#            M.append(np.arange(min(df['mag']),max(df['mag'])+2*Mbin,Mbin))
#            R.append(np.arange(min(df['dist']),max(df['dist'])+2*dbin,dbin))
            M.append(df['mag'])
            R.append(df['dist'])

    # If requested, create a results file also
    with open(output_filename, 'wb') as file:
        pickle.dump([lon, lat, im, Tr, M, R, apoe_norm, modeLst, meanLst], file)

    # Create a set of outputs
    return lon, lat, im, Tr, M, R, apoe_norm, modeLst, meanLst

def ensure_dir(file_path):
    # procedure to control if the folder path exist. 
    # If it does not the path will be created
    import os
    if not os.path.exists(file_path):
        os.makedirs(file_path)

def plot_disagg(Mbin,dbin,n_rows):
    """
    Details
    -------
    This script will save disaggregation plots
    including M and R.
    
    Information
    -----------
    Author: Volkan Ozsarac
    First Version: August 2020
    
    Parameters
    ----------
    Mbin : int, float
        magnitude bin used in disaggregation.
    dbin : int, float
        distance bin used in disaggregation.
    n_rows : int
        total number of rows for subplots.

    Returns
    -------
    None.

    """
	# lets add the plotting options to make everything clearer (VO)
    from mpl_toolkits.mplot3d import axes3d
    import matplotlib.pyplot as plt
    from matplotlib import cm #import colormap
    from matplotlib import style # import syle
    import os
    import numpy as np
    import math

    cwd = os. getcwd()    
    style.use('ggplot')
    cmap = cm.get_cmap('jet') # Get desired colormap
    # cmap = cm.get_cmap('Spectral')

    output_dir = os.path.join(cwd,'Hazard_Info')
    ensure_dir(output_dir)
    fname = os.path.join(output_dir,'disagg_results.pkl')
    
    path_disagg_results = path_hazard_results = os.path.join(cwd,'OpenQuake Model','Outputs')
    lon, lat, im, Tr, M, R, apoe_norm, modeLst, meanLst = process_OQ_disagg(Mbin,dbin,path_disagg_results,fname)

    lon = [x for _,x in sorted(zip(Tr,lon))]
    lat = [x for _,x in sorted(zip(Tr,lat))]
    im = [x for _,x in sorted(zip(Tr,im))]    
    M = [x for _,x in sorted(zip(Tr,M))]
    R = [x for _,x in sorted(zip(Tr,R))]
    apoe_norm = [x for _,x in sorted(zip(Tr,apoe_norm))]
    modeLst = [x for _,x in sorted(zip(Tr,modeLst))]
    meanLst = [x for _,x in sorted(zip(Tr,meanLst))]
    Tr = sorted(Tr)

    n_Tr=len(np.unique(np.asarray(Tr)))
    ims=np.unique(im); n_im=len(ims)
    
    lon = lon[0]
    lat = lat[0]
    
    mags = []
    dists = []
    
    n_cols = math.floor(n_Tr/n_rows)
    if np.mod(n_Tr,n_rows):
        n_cols += 1
    
    for idx1 in range(n_im):
        fig = plt.figure(figsize=(19.2, 10.8))
        for idx2 in range(n_Tr):
            i = idx1*n_Tr+idx2
            ax1 = fig.add_subplot(n_rows,n_cols,idx2+1, projection='3d')
            
            X = R[i]
            Y = M[i]
            Z = np.zeros(len(X))
            
            dx = np.ones(len(X))*dbin/2
            dy = np.ones(len(X))*Mbin/2
            dz = apoe_norm[i]*100
            
            # here we may make the colormap based on epsilon instead of hazard contribution
            max_height = np.max(dz)   # get range of colorbars so we can normalize
            min_height = np.min(dz)
            # scale each z to [0,1], and get their rgb values
            rgba = [cmap((k-min_height)/max_height) for k in dz] 
            ax1.bar3d(X, Y, Z, dx, dy, dz, color=rgba, zsort='average',alpha=0.7, shade=True)
            
            ax1.set_xlabel('R [km]')
            ax1.set_ylabel('$M_{w}$')
            if np.mod(idx2+1,n_cols)==1:
                ax1.set_zlabel('Hazard Contribution [%]')
                ax1.zaxis.set_rotate_label(False)  # disable automatic rotation
                ax1.set_zlabel('Hazard Contribution [%]',rotation=90)
            ax1.zaxis._axinfo['juggled'] = (1,2,0)
            
            plt.title('$T_{R}$=%s years\n$M_{mod}$=%s, $R_{mod}$=%s km\n$M_{mean}$=%s, $R_{mean}$=%s km' \
                      % ("{:.0f}".format(Tr[i]),"{:.2f}".format(modeLst[i][0]),"{:.0f}".format(modeLst[i][1]),\
                         "{:.2f}".format(meanLst[i][0]),"{:.0f}".format(meanLst[i][1])), \
                          fontsize=11, loc='right',verticalalignment='top')
        
            mags.append(meanLst[i][0]); dists.append(meanLst[i][1])
        
        plt.subplots_adjust(hspace = 0.1, wspace = 0.05) #adjust the subplot to the right for the legend
        fig.suptitle('Disaggregation of Seismic Hazard\nIntensity Measure: %s\nLatitude: %s, Longitude: %s' % (ims[idx1],"{:.4f}".format(lat),"{:.4f}".format(lon)), fontsize=14, weight='bold',ha='left',x=0.12,y=0.97)
        
        fname=os.path.join(output_dir,ims[idx1]+'.png')
        plt.savefig(fname)
        
    fname=os.path.join(output_dir,'mean_mags.out')
    np.savetxt(fname,np.asarray(mags),fmt='%.2f')
    fname=os.path.join(output_dir,'mean_dists.out')
    np.savetxt(fname,np.asarray(dists),fmt='%.1f')