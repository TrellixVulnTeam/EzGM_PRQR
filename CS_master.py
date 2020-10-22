"""
|-----------------------------------------------------------------------|
|                                                                       |
|    Conditional spectrum based                                         |
|    record selection and scaling                                       |
|    Version: 0.3                                                       |
|                                                                       |
|    Created on 21/10/2020                                              |
|    Author: Volkan Ozsarac                                             |
|    Affiliation: University School for Advanced Studies IUSS Pavia     |
|    Earthquake Engineering PhD Candidate                               |
|                                                                       |
|-----------------------------------------------------------------------|
"""

# Import standard python libraries
from __future__ import division
import sys
import os
import shutil
import zipfile
import numpy as np
import numpy.matlib
from scipy.stats import skew
from time import gmtime, time, sleep
import matplotlib.pyplot as plt
import matplotlib
from scipy.io import loadmat
from scipy import interpolate
import pickle
import copy
# Import the tools from OpenQuake
from openquake.hazardlib import gsim, imt, const
from selenium import webdriver
import requests

startTime = time()

class cs_master:
    
    def __init__(self, Tstar = 0.5, gmpe = 'Boore_Atkinson_2008', database = 'NGA_W1', T_resample = [0,0.05], pInfo = 1):
        """
        
        Details
        -------
        Loads the database and add spectral values for Tstar 
        if they are not present via interpolation.
        
        Parameters
        ----------
        Tstar    : int, float, list, the default is None.
            Conditioning period range [sec].
        gmpe     : str, optional
            GMPE model (see OpenQuake library). 
            The default is 'Boore_Atkinson_2008'.
        database : str, optional
            database to use, NGA_W1, NGA_W2, EXSIM_Duzce, etc.
            The default is NGA_W1.
       T_resample: list, optional
            flag to create a new uniform period array with step size T_resample[1] sec
            The spectral values will be interpolated for this new period array
            The default = [0,0.1]. If T_resample[0] = 0 existing period array will be used.           
        pInfo    : int, optional
            flag to print required input for the gmpe which is going to be used. 
            (0: no, 1:yes)
            The default is 1.
            
        Returns
        -------
        None.
        
        """
        
        # add Tstar to self
        if isinstance(Tstar,int) or isinstance(Tstar,float):
            self.Tstar = np.array([Tstar])
        elif isinstance(Tstar,list): 
            self.Tstar = np.asarray(Tstar)
        
        # Add the input the ground motion database to use
        matfile = os.path.join('Meta_Data',database)
        self.database = loadmat(matfile, squeeze_me=True)
        self.database['Name'] = database
        
        # Resample the period array and the spectra via interpolation
        if T_resample[0]:
            step = T_resample[1]
            Periods = np.append(np.array([0.01, 0.02]),np.arange(step,self.database['Periods'][-1],step))
            f = interpolate.interp1d(self.database['Periods'], self.database['Sa_1'],axis=1)            
            Sa_int = f(Periods)
            temp = self.database['Sa_1'][:,-1].reshape(len(self.database['Sa_1'][:,-1]),1)
            self.database['Sa_1'] = np.append(Sa_int, temp, axis=1)
    
            if database.startswith("NGA"):
                f = interpolate.interp1d(self.database['Periods'], self.database['Sa_2'],axis=1)            
                Sa_int = f(Periods)
                temp = self.database['Sa_2'][:,-1].reshape(len(self.database['Sa_2'][:,-1]),1)
                self.database['Sa_2'] = np.append(Sa_int, temp, axis=1)
                
                f = interpolate.interp1d(self.database['Periods'], self.database['Sa_RotD50'],axis=1)            
                Sa_int = f(Periods)
                temp = self.database['Sa_RotD50'][:,-1].reshape(len(self.database['Sa_RotD50'][:,-1]),1)
                self.database['Sa_RotD50'] = np.append(Sa_int, temp, axis=1)
                
            self.database['Periods'] = np.append(Periods,self.database['Periods'][-1])
        
        # check if AvgSa or Sa is used as IM, 
        # then in case of Sa(T*) add T* and Sa(T*) if not present
        if not self.Tstar[0] in self.database['Periods'] and len(self.Tstar) == 1: 
            f = interpolate.interp1d(self.database['Periods'], self.database['Sa_1'],axis=1)            
            Sa_int = f(self.Tstar[0]); Sa_int.shape = (len(Sa_int),1)           
            Sa = np.append(self.database['Sa_1'], Sa_int, axis=1)
            Periods = np.append(self.database['Periods'],self.Tstar[0])            
            self.database['Sa_1'] = Sa[:,np.argsort(Periods)]

            if database.startswith("NGA"):
                f = interpolate.interp1d(self.database['Periods'], self.database['Sa_2'],axis=1)
                Sa_int = f(self.Tstar[0]); Sa_int.shape = (len(Sa_int),1)
                Sa = np.append(self.database['Sa_2'], Sa_int, axis=1)
                self.database['Sa_2'] = Sa[:,np.argsort(Periods)]  
                
                f = interpolate.interp1d(self.database['Periods'], self.database['Sa_RotD50'],axis=1)
                Sa_int = f(self.Tstar[0]); Sa_int.shape = (len(Sa_int),1)
                Sa = np.append(self.database['Sa_RotD50'], Sa_int, axis=1)
                self.database['Sa_RotD50'] = Sa[:,np.argsort(Periods)]  

            self.database['Periods'] = Periods[np.argsort(Periods)]
            
        # Define the GMPE object and print the required input information
        # More can be added here
        if gmpe == 'Boore_Atkinson_2008':
            self.bgmpe = gsim.boore_atkinson_2008.BooreAtkinson2008()
        if gmpe == 'Boore_EtAl_2014':
            self.bgmpe = gsim.boore_2014.BooreEtAl2014()
        if gmpe == 'Akkar_EtAlRjb_2014':
            self.bgmpe = gsim.akkar_2014.AkkarEtAlRjb2014()
        if gmpe == 'AkkarCagnan2010':            
            self.bgmpe = gsim.akkar_cagnan_2010.AkkarCagnan2010()
        if gmpe == 'ChiouYoungs2008':
            self.bgmpe = gsim.chiou_youngs_2008.ChiouYoungs2008()
        if gmpe == 'CampbellBozorgnia2008':            
            self.bgmpe = gsim.campbell_bozorgnia_2008.CampbellBozorgnia2008()
        if gmpe == 'ChiouYoungs2014':
            self.bgmpe = gsim.chiou_youngs_2014.ChiouYoungs2014()
        if gmpe == 'CampbellBozorgnia2014':            
            self.bgmpe = gsim.campbell_bozorgnia_2014.CampbellBozorgnia2014()
        if gmpe == 'Idriss2014':
            self.bgmpe = gsim.idriss_2014.Idriss2014()
        if gmpe == 'AbrahamsonEtAl2014':
            self.bgmpe = gsim.abrahamson_2014.AbrahamsonEtAl2014()
    
        if pInfo == 1:  # print the selected gmpe info
            print('The required distance parameters for this gmpe are: %s' % list(self.bgmpe.REQUIRES_DISTANCES))
            print('The required rupture parameters for this gmpe are: %s' % list(self.bgmpe.REQUIRES_RUPTURE_PARAMETERS))
            print('The required site parameters for this gmpe are: %s' % list(self.bgmpe.REQUIRES_SITES_PARAMETERS))
            print('The defined intensity measure component is: %s' % self.bgmpe.DEFINED_FOR_INTENSITY_MEASURE_COMPONENT)
            print('The defined tectonic region type is: %s' % self.bgmpe.DEFINED_FOR_TECTONIC_REGION_TYPE)

    def create(self, site_param = {'vs30': 520}, rup_param = {'rake': 0.0, 'mag': [7.2, 6.5]}, 
               dist_param = {'rjb': [20, 5]}, Hcont=[0.6,0.4], T_Tgt_range  = [0.01,4], 
               im_Tstar = 2.0, epsilon = None, cond = 1, useVar = 1, outdir = 'Outputs'):
        """
        
        Details
        -------
        Creates the target spectrum (conditional or unconditional).
    
        Notes
        -----
        Requires libraries from openquake.
        
        References
        ----------
        Baker JW. Conditional Mean Spectrum: Tool for Ground-Motion Selection.
        Journal of Structural Engineering 2011; 137(3): 322–331.
        DOI: 10.1061/(ASCE)ST.1943-541X.0000215.

        Parameters
        ----------
        site_param : dictionary
            Contains required site parameters to define target spectrum.
        rup_param  : dictionary
            Contains required rupture parameters to define target spectrum.
        dist_param : dictionary
            Contains required distance parameters to define target spectrum.
        Hcont      : list, optional, the default is None.
            Hazard contribution for considered scenarios. 
            If None hazard contribution is the same for all scenarios.
        im_Tstar   : int, float, optional, the default is 1.
            Conditioning intensity measure level [g] (conditional selection)
        epsilon    : list, optional, the default is None.
            Epsilon values for considered scenarios (conditional selection)
        T_Tgt_range: list, optional, the default is [0.01,4].
            Lower and upper bound values for the period range of target spectrum.
        cond       : int, optional
            0 to run unconditional selection
            1 to run conditional selection
        useVar     : int, optional, the default is 1.
            0 not to use variance in target spectrum
            1 to use variance in target spectrum
        outdir     : str, optional, the default is 'Outputs'.
            output directory to create.

        Returns
        -------
        None.
                                        
        """
        # create the output directory and add the path to self
        cwd = os. getcwd()
        outdir_path = os.path.join(cwd,outdir)
        self.outdir = outdir_path
        create_outdir(self.outdir)
        
        # add target spectrum settings to self
        self.cond = cond
        self.useVar = useVar
        
        # Get number of scenarios, and their contribution
        nScenarios = len(rup_param['mag'])
        if Hcont is None:
            self.Hcont = [1/nScenarios for _ in range(nScenarios)]
        else:
            self.Hcont = Hcont
        
        # Period range of the target spectrum
        temp = np.abs(self.database['Periods'] - np.min(T_Tgt_range))
        idx1 = np.where(temp==np.min(temp))[0][0]
        temp = np.abs(self.database['Periods'] - np.max(T_Tgt_range))
        idx2 = np.where(temp==np.min(temp))[0][0]
        T_Tgt = self.database['Periods'][idx1:idx2+1]

        if cond == 0:
            del self.Tstar
            
        elif len(self.Tstar) != 1:
            # Define the array for AvgSa periods
            Tlower = np.min(self.Tstar); temp = np.abs(T_Tgt-Tlower)
            idx1 = np.where(temp==np.min(temp))[0][0]
            Tupper = np.max(self.Tstar); temp = np.abs(T_Tgt-Tupper)
            idx2 = np.where(temp==np.min(temp))[0][0]
            self.Tstar = T_Tgt[idx1:idx2+1]

        # Get number of scenarios, and their contribution
        Hcont_mat = np.matlib.repmat(np.asarray(self.Hcont),len(T_Tgt),1)
        
        # Conditional spectrum, log parameters
        TgtMean = np.zeros((len(T_Tgt),nScenarios))

        # Covariance
        TgtCov = np.zeros((nScenarios,len(T_Tgt),len(T_Tgt)))
        
        for n in range(nScenarios):

            # gmpe spectral values
            mu_lnSaT = np.zeros(len(T_Tgt))
            sigma_lnSaT = np.zeros(len(T_Tgt))
            
            # correlation coefficients
            rho_T_Tstar = np.zeros(len(T_Tgt))

            # Covariance
            Cov = np.zeros((len(T_Tgt),len(T_Tgt)))
            
            # Set the contexts for the scenario
            sites = gsim.base.SitesContext()
            for key in site_param.keys():
                temp = np.array([site_param[key]])
                setattr(sites, key, temp)
            
            rup = gsim.base.RuptureContext()
            for key in rup_param.keys():
                if key == 'mag':
                    temp = np.array([rup_param[key][n]])
                else:                     
                    temp = np.array([rup_param[key]])
                setattr(rup, key, temp)
                    
            dists = gsim.base.DistancesContext()
            for key in dist_param.keys():
                if key == 'rjb':
                    temp = np.array([dist_param[key][n]])
                else:                     
                    temp = np.array([dist_param[key]]) 
                setattr(dists, key, temp)
                
            scenario = [sites,rup,dists]
        
            for i in range(len(T_Tgt)):
                # Get the GMPE ouput for a rupture scenario
                mu0, sigma0 = self.bgmpe.get_mean_and_stddevs(sites, rup, dists, imt.SA(period=T_Tgt[i]), [const.StdDev.TOTAL])
                mu_lnSaT[i] = mu0[0]
                sigma_lnSaT[i] = sigma0[0][0]
                
                if self.cond == 1:
                    # Compute the correlations between each T and Tstar
                    rho_T_Tstar[i] = rho_AvgSA_SA(self.bgmpe,scenario,T_Tgt[i],self.Tstar)
            
            if self.cond == 1:
                # Get the GMPE output and calculate Avg_Sa_Tstar
                mu_lnSaTstar,sigma_lnSaTstar = Sa_avg(self.bgmpe,scenario,self.Tstar)
                
                if epsilon is None:
                    # Back calculate epsilon
                    rup_eps = (np.log(im_Tstar) - mu_lnSaTstar) / sigma_lnSaTstar
                else:
                    rup_eps = epsilon[n]
                    
                # Get the value of the ln(CMS), conditioned on T_star
                TgtMean[:,n] = mu_lnSaT + rho_T_Tstar * rup_eps * sigma_lnSaT
                
            elif self.cond == 0:
                TgtMean[:,n] = mu_lnSaT 
        
            for i in range(len(T_Tgt)):
                for j in range(len(T_Tgt)):
                    
                    var1 = sigma_lnSaT[i] ** 2
                    var2 = sigma_lnSaT[j] ** 2
                    # using Baker & Jayaram 2008 as correlation model
                    sigma_Corr = Baker_Jayaram_2008(T_Tgt[i], T_Tgt[j]) * np.sqrt(var1 * var2)
                    
                    if self.cond == 1:
                        varTstar = sigma_lnSaTstar ** 2
                        sigma11 = np.matrix([[var1, sigma_Corr], [sigma_Corr, var2]])
                        sigma22 = np.array([varTstar])
                        sigma12 = np.array([rho_T_Tstar[i] * np.sqrt(var1 * varTstar), rho_T_Tstar[j] * np.sqrt(varTstar * var2)])
                        sigma12.shape = (2,1); sigma22.shape = (1,1)
                        sigma_cond = sigma11 - sigma12 * 1. / (sigma22) * sigma12.T
                        Cov[i, j] = sigma_cond[0, 1]
                        
                    elif self.cond == 0:
                        Cov[i, j] = sigma_Corr

            # Get the value of standard deviation of target spectrum
            TgtCov[n,:,:] = Cov

        # over-write coveriance matrix with zeros if no variance is desired in the ground motion selection
        if self.useVar == 0:
            TgtCov = np.zeros(TgtCov.shape)
            
        TgtMean_fin = np.sum(TgtMean*Hcont_mat,1)
        # all 2D matrices are the same for each kk scenario, since sigma is only T dependent
        TgtCov_fin = TgtCov[0,:,:]
        Cov_elms = np.zeros((len(T_Tgt),nScenarios))
        for ii in range(len(T_Tgt)):
            for kk in range(nScenarios):
                # Hcont[kk] = contribution of the k-th scenario
                Cov_elms[ii,kk] = (TgtCov[kk,ii,ii]+(TgtMean[ii,kk]-TgtMean_fin[ii])**2) * self.Hcont[kk] 

        cov_diag=np.sum(Cov_elms,1)
        TgtCov_fin[np.eye(len(T_Tgt))==1] = cov_diag

        # Find covariance values of zero and set them to a small number so that
        # random number generation can be performed
        TgtCov_fin[np.abs(TgtCov_fin)<1e-10] = 1e-10
        
        TgtSigma_fin = np.sqrt(np.diagonal(TgtCov_fin))
        TgtSigma_fin[np.isnan(TgtSigma_fin)] = 0

        # Add target spectrum to self
        self.mu_ln = TgtMean_fin
        self.sigma_ln = TgtSigma_fin
        self.T = T_Tgt
        self.cov = TgtCov_fin

        if cond == 1:
            # add intensity measure level to self
            if epsilon is None:
                self.im_Tstar = im_Tstar
            else:
                # indices where IM is going to be calculated
                ind = []
                for k in range(len(self.Tstar)):
                    ind.append(np.where(self.T == self.Tstar[k])[0][0])
                self.im_Tstar = np.exp(np.sum(self.mu_ln[ind])/len(self.Tstar))
                self.epsilon = epsilon
        
        print('Coniditonal spectrum is created.')

    def simulate_spectra(self):
        """
        Details
        -------
        Generates simulated response spectra with best matches to the target values.

        Parameters
        ----------

        Returns
        -------
        None.
        
        Notes
        -----
                     
        """
        
        # Set initial seed for simulation
        if self.seedValue != 0:
            np.random.seed(0)
        else:
            np.random.seed(sum(gmtime()[:6]))

        devTotalSim = np.zeros((self.nTrials,1))
        specDict = {}
        nT = len(self.T)
        # Generate simulated response spectra with best matches to the target values
        for j in range(self.nTrials):
            specDict[j] = np.zeros((self.nGM,nT))
            for i in range(self.nGM):
                # Note: we may use latin hypercube sampling here instead. I leave it as Monte Carlo for now
                specDict[j][i,:] = np.exp(np.random.multivariate_normal(self.mu_ln,self.cov))
                
            devMeanSim = np.mean(np.log(specDict[j]), axis = 0) - self.mu_ln # how close is the mean of the spectra to the target
            devSigSim = np.std(np.log(specDict[j]), axis=0) -  self.sigma_ln # how close is the mean of the spectra to the target
            devSkewSim = skew(np.log(specDict[j]), axis=0)                   # how close is the skewness of the spectra to zero (i.e., the target)
            
            devTotalSim[j] = self.weights[0] * np.sum(devMeanSim**2)  + \
                             self.weights[1] * np.sum(devSigSim**2)   + \
                             0.1 * (self.weights[2]) * np.sum(devSkewSim**2) # combine the three error metrics to compute a total error

        recUse = np.argmin(np.abs(devTotalSim))   # find the simulated spectra that best match the targets 
        self.sim_spec = np.log(specDict[recUse])  # return the best set of simulations

    def search_database(self):
        """
        
        Details
        -------
        Search the database and does the filtering.
        
        Parameters
        ----------

        Returns
        -------
        sampleBig : numpy.ndarray
            An array which contains the IMLs from filtered database.
        soil_Vs30 : numpy.ndarray
            An array which contains the Vs30s from filtered database.
        magnitude : numpy.ndarray
            An array which contains the magnitudes from filtered database.
        Rjb : numpy.ndarray
            An array which contains the Rjbs from filtered database.
        mechanism : numpy.ndarray
            An array which contains the fault type info from filtered database.
        Filename_1 : numpy.ndarray
            An array which contains the filename of 1st gm component from filtered database.
            If selection is set to 1, it will include filenames of both components.
        Filename_2 : numpy.ndarray
            An array which contains the filename of 2nd gm component filtered database.
            If selection is set to 1, it will be None value.
        NGA_num : numpy.ndarray
			If NGA_W2 is used as record database, record sequence numbers from filtered
			database will be saved, for other databases this variable is None.
        """
        
        if self.selection == 1: # SaKnown = Sa_arb

            if self.database['Name'].startswith('NGA'):
            
                SaKnown    = np.append(self.database['Sa_1'],self.database['Sa_2'], axis=0)
                soil_Vs30  = np.append(self.database['soil_Vs30'], self.database['soil_Vs30'], axis=0)
                Mw         = np.append(self.database['magnitude'], self.database['magnitude'], axis=0)   
                Rjb        = np.append(self.database['Rjb'], self.database['Rjb'], axis=0)  
                fault      = np.append(self.database['mechanism'], self.database['mechanism'], axis=0)
                Filename_1 = np.append(self.database['Filename_1'], self.database['Filename_2'], axis=0)
                
                if self.database['Name'] == 'NGA_W2':
                    NGA_num = np.append(self.database['NGA_num'],self.database['NGA_num'], axis=0)
            
            elif self.database['Name'].startswith("EXSIM"):
                SaKnown    = self.database['Sa_1']
                soil_Vs30  = self.database['soil_Vs30']
                Mw         = self.database['magnitude']
                Rjb        = self.database['Rjb']
                fault      = self.database['mechanism']
                Filename_1 = self.database['Filename_1']
    
        if self.selection == 2: # SaKnown = Sa_g.m.
            if self.Sa_def == 'GeoMean':
                SaKnown = np.sqrt(self.database['Sa_1']*self.database['Sa_2'])
            elif 'RotD50': # SaKnown = Sa_RotD50.
                SaKnown = self.database['Sa_RotD50']
            elif self.Sa_def[:4] == 'RotD': # SaKnown = Sa_RotDxx.
                xx = int(self.Sa_def[4:])
                SaKnown = get_RotDxx(self.database['Sa_1'], self.database['Sa_2'], xx, num_theta = 100)
                
            soil_Vs30  = self.database['soil_Vs30']
            Mw         = self.database['magnitude']
            Rjb        = self.database['Rjb']
            fault      = self.database['mechanism']
            Filename_1 = self.database['Filename_1']
            Filename_2 = self.database['Filename_2']
            
            if self.database['Name'] == 'NGA_W2':
                NGA_num = self.database['NGA_num']
                
        perKnown = self.database['Periods']        
        
        # Limiting the records to be considered using the `notAllowed' variable
        # notAllowed = []
        # Sa cannot be negative or zero, remove these.
        notAllowed = np.unique(np.where(SaKnown <= 0)[0]).tolist()
        
        # remove these as J. Baker does for this metadata
        if self.database['Name'] == "NGA_W2":
            temp1 = np.arange(4576,4839,1)
            temp2 = np.arange(6992,8055,1)
            temp3 = np.array([9193])
            notAllowed.extend(temp1.tolist())
            notAllowed.extend(temp2.tolist())
            notAllowed.extend(temp3.tolist())
            if self.selection == 1:
                notAllowed.extend((self.database['NGA_num'][-1]+temp1).tolist())
                notAllowed.extend((self.database['NGA_num'][-1]+temp2).tolist())
                notAllowed.extend((self.database['NGA_num'][-1]+temp3).tolist())               
            
        if not self.Vs30_lim is None: # limiting values on soil exist
            mask = (soil_Vs30 > min(self.Vs30_lim)) & (soil_Vs30 < max(self.Vs30_lim))
            temp = [i for i, x in enumerate(mask) if not x]
            notAllowed.extend(temp)

        if not self.Mw_lim is None: # limiting values on magnitude exist
            mask = (Mw > min(self.Mw_lim)) & (Mw < max(self.Mw_lim))
            temp = [i for i, x in enumerate(mask) if not x]
            notAllowed.extend(temp)

        if not self.Rjb_lim is None: # limiting values on Rjb exist
            mask = (Rjb > min(self.Rjb_lim)) & (Rjb < max(self.Rjb_lim))
            temp = [i for i, x in enumerate(mask) if not x]
            notAllowed.extend(temp)
            
        if not self.fault_lim is None: # limiting values on mechanism exist
            mask = (fault == self.fault_lim)
            temp = [i for i, x in enumerate(mask) if not x]
            notAllowed.extend(temp)
        
        # get the unique values
        notAllowed = (list(set(notAllowed)))
        Allowed = [i for i in range(SaKnown.shape[0])]
        for i in notAllowed:
            Allowed.remove(i)
            
        # Use only allowed records
        SaKnown    = SaKnown[Allowed,:]
        soil_Vs30  = soil_Vs30[Allowed]
        Mw         = Mw[Allowed]
        Rjb        = Rjb[Allowed]
        fault      = fault[Allowed]
        Filename_1 = Filename_1[Allowed]
        
        if self.selection == 1:
            Filename_2 = None
        else:
            Filename_2 = Filename_2[Allowed]

        if self.database['Name'] == "NGA_W2":
            NGA_num    = NGA_num[Allowed]
        else:
            NGA_num = None
        
        # Arrange the available spectra in a usable format and check for invalid input
        # Match periods (known periods and periods for error computations)
        recPer = []
        for i in range(len(self.T)):
            recPer.append(np.where(perKnown == self.T[i])[0][0])
        
        # Check for invalid input
        sampleBig = SaKnown[:,recPer]
        if np.any(np.isnan(sampleBig)):
            print('NaNs found in input response spectra')
            sys.exit()
            
        return sampleBig, soil_Vs30, Mw, Rjb, fault, Filename_1, Filename_2, NGA_num
        
    def select(self, nGM=30, selection=1, Sa_def='RotD50', isScaled = 1, maxScale = 4,
               Mw_lim=None, Vs30_lim=None, Rjb_lim=None, fault_lim=None,
               nTrials = 20,  weights = [1,2,0.3], seedValue  = 0, 
               nLoop = 2, penalty = 0, tol = 10):
        """
        
        Details
        -------
        Perform the ground motion selection.
        
        Parameters
        ----------
        nGM : int, optional, the default is 30.
            Number of ground motions to be selected.
        selection : int, optional, The default is 1.
            1 for single-component selection and arbitrary component sigma.
            2 for two-component selection and average component sigma. 
        Sa_def : str, optional, the default is 'RotD50'.
            The spectra definition. Necessary if selection = 2.
            'GeoMean' or 'RotDxx', where xx the percentile to use. 
        isScaled : int, optional, the default is 1.
            0 not to allow use of amplitude scaling for spectral matching.
            1 to allow use of amplitude scaling for spectral matching.
        maxScale : float, optional, the default is 4.
            The maximum allowable scale factor
        Mw_lim : list, optional, the default is None.
            The limiting values on magnitude. 
        Vs30_lim : list, optional, the default is None.
            The limiting values on Vs30. 
        Rjb_lim : list, optional, the default is None.
            The limiting values on Rjb. 
        mechanism_lim : int, optional, the default is None.
            The limiting fault mechanism. 
            0 for unspecified fault 
            1 for strike-slip fault
            2 for normal fault
            3 for reverse fault
        seedValue  : int, optional, the default is 0.
            For repeatability. For a particular seedValue not equal to
            zero, the code will output the same set of ground motions.
            The set will change when the seedValue changes. If set to
            zero, the code randomizes the algorithm and different sets of
            ground motions (satisfying the target mean and variance) are
            generated each time.
        weights : numpy.ndarray or list, optional, the default is [1,2,0.3].
            Weights for error in mean, standard deviation and skewness
        nTrials : int, optional, the default is 20.
            nTrials sets of response spectra are simulated and the best set (in terms of
            matching means, variances and skewness is chosen as the seed). The user
            can also optionally rerun this segment multiple times before deciding to
            proceed with the rest of the algorithm. It is to be noted, however, that
            the greedy improvement technique significantly improves the match between
            the means and the variances subsequently.
        nLoop   : int, optional, the default is 2.
            Number of loops of optimization to perform.
        penalty : int, optional, the default is 0.
            > 0 to penalize selected spectra more than 
            3 sigma from the target at any period, = 0 otherwise.
        tol     : int, optional, the default is 10.
            Tolerable percent error to skip optimization 

        Returns
        -------
        None.

        """
        
        # Add selection settings to self
        self.nGM = nGM
        self.selection = selection
        self.Sa_def = Sa_def
        self.isScaled = isScaled
        self.Mw_lim = Mw_lim
        self.Vs30_lim = Vs30_lim
        self.Rjb_lim = Rjb_lim
        self.fault_lim = fault_lim
        self.seedValue = seedValue
        self.weights = weights
        self.nTrials = nTrials
        self.maxScale = maxScale
        self.nLoop = nLoop
        self.tol = tol
        self.penalty = penalty
        
        # Exsim provides a single gm component
        if self.database['Name'].startswith("EXSIM"):
            self.selection = 1
        
        # Simulate response spectra
        self.simulate_spectra() 
        
        # Search the database and filter
        sampleBig, Vs30, Mw, Rjb, fault, Filename_1, Filename_2, NGA_num = self.search_database()
        
        # Processing available spectra
        sampleBig = np.log(sampleBig)
        nBig = sampleBig.shape[0]
        
        # Find best matches to the simulated spectra from ground-motion database
        recID = np.ones((self.nGM), dtype = int)*(-1)
        finalScaleFac = np.ones((self.nGM))
        sampleSmall = np.ones((self.nGM,sampleBig.shape[1]))
        
        if self.cond == 1:
            ind1 = [] # indices where IML is going to be calculated
            ind2 = [] # indices where IML is not going to be calculated
            for k in range(len(self.Tstar)):
                ind1.append(np.where(self.T == self.Tstar[k])[0][0])
                ind2.append(np.where(self.T != self.Tstar[k])[0][0])
        
        # Find nGM ground motions, inital subset
        for i in range(self.nGM):
            err = np.zeros((nBig))
            scaleFac = np.ones((nBig))
            
            # From the sample of ground motions
            for j in range(nBig):
                
                if self.isScaled == 1: # Calculate scaling facator
                
                    if self.cond == 1: # Calculate using conditioning IML
                        rec_iml=np.exp(np.sum(sampleBig[j,ind1])/len(self.Tstar))
                        scaleFac[j] = self.im_Tstar/rec_iml
                        
                    elif self.cond == 0: # Calculate using minimization of mean squared root error
                        scaleFac[j] = np.sum(np.exp(sampleBig[j,:])*np.exp(self.sim_spec[i,:]))/np.sum(np.exp(sampleBig[j,:])**2)

                # check if scaling factor is greater than the limit                
                # check if this record have already been selected
                if np.any(recID == j) or scaleFac[j] > self.maxScale:
                    err[j] = 1000000
                else: # calculate the error
                    err[j] = np.sum((np.log(np.exp(sampleBig[j,:])*scaleFac[j]) - self.sim_spec[i,:])**2)
                    
            recID[i] = int(np.argsort(err)[0])    
            if err.min() >= 1000000:
                print('Warning: Possible problem with simulated spectrum. No good matches found')
                print(recID[i])
                sys.exit()

            if self.isScaled == 1:
                finalScaleFac[i] = scaleFac[recID[i]]
            
            # Save the selected spectra
            sampleSmall[i,:] = np.log(np.exp(sampleBig[recID[i],:])*finalScaleFac[i])
            
        # Optimizing the selected subset of ground motions
        # Currently only option is to use Greedy subset modification procedure
        # This seems to be sufficient enough
        for k in range(self.nLoop): # Number of passes
            
            for i in range(self.nGM): # Loop for nGM
                
                minDev = 100000
                scaleFac = np.ones((nBig))
                sampleSmall = np.delete(sampleSmall, i, 0)
                recID = np.delete(recID, i)
                
                # Try to add a new spectra to the subset list
                for j in range(nBig):
                    # Get the scaling factor and do the scaling
                    if self.isScaled == 1:

                        if self.cond == 1: # Calculate using conditioning IML
                            # Calculate the intensity measure level (AvgSa or Sa)
                            rec_Avg=np.exp(np.sum(sampleBig[j,ind1])/len(self.Tstar))
                            scaleFac[j] = self.im_Tstar/rec_Avg
                        
                        elif self.cond == 0: # Calculate using minimization of mean squared root error
                            scaleFac[j] = np.sum(np.exp(sampleBig[j,:])*np.exp(self.sim_spec[i,:]))/np.sum(np.exp(sampleBig[j,:])**2)
                        
                    sampleSmall = np.concatenate((sampleSmall,sampleBig[j,:].reshape(1,sampleBig.shape[1]) + np.log(scaleFac[j])),axis=0)

                    # Greedy subset modification procedure
                    devMean = np.mean(sampleSmall,axis=0) - self.mu_ln # Compute deviations from target
                    devSig = np.std(sampleSmall, axis=0) - self.sigma_ln
                    devTotal = weights[0] * np.sum(devMean**2) + weights[1] * np.sum(devSig**2)
                    
                    # Penalize bad spectra (set penalty to zero if this is not required)
                    if self.penalty > 0:
                        for m in range(sampleSmall.shape[0]):
                            devTotal += np.sum(np.abs(np.exp(sampleSmall[m,:]) > np.exp(self.mu_ln + 3*self.sigma_ln))) * penalty
                    
                    # Check if we exceed the scaling limit
                    if scaleFac[j] > self.maxScale or np.any(np.array(recID) == j):
                        devTotal += 1000000
                    
                    # Should cause improvement and record should not be repeated
                    if devTotal < minDev:
                        minID = j
                        minDev = devTotal
                    
                    # Empty the slot to try a new candidate
                    sampleSmall = np.delete(sampleSmall, -1, 0)
                
                # Add new element in the right slot
                if self.isScaled == 1:
                    finalScaleFac[i] = scaleFac[minID]
                else:
                    finalScaleFac[i] = 1
                sampleSmall = np.concatenate((sampleSmall[:i,:], sampleBig[minID,:].reshape(1,sampleBig.shape[1]) + np.log(scaleFac[minID]), 
                                sampleSmall[i:,:]),axis=0)
                recID = np.concatenate((recID[:i],np.array([minID]),recID[i:]))
            
            # Lets check if the selected ground motions are good enough, if the errors are sufficiently small stop!
            if self.cond == 1 and len(ind1) == 1: # if conditioned on SaT, ignore error at T*
                medianErr = np.max(np.abs(np.exp(np.mean(sampleSmall[:,ind2],axis=0)) - np.exp(self.mu_ln[ind2]))/np.exp(self.mu_ln[ind2]))*100
                stdErr = np.max(np.abs(np.std(sampleSmall[:,ind2], axis=0) - self.sigma_ln[ind2])/self.sigma_ln[ind2])*100  
            else:
                medianErr = np.max(np.abs(np.exp(np.mean(sampleSmall,axis=0)) - np.exp(self.mu_ln))/np.exp(self.mu_ln))*100
                stdErr = np.max(np.abs(np.std(sampleSmall, axis=0) - self.sigma_ln)/self.sigma_ln)*100

            if medianErr < self.tol and stdErr < self.tol:
                break
        print('Ground Motion selection is finished')
        print('For T ∈ [%.2f - %2.f]'% (self.T[0],self.T[-1]))
        print('Max error in median = %.2f %%' % medianErr)
        print('Max error in standard deviation = %.2f %%' % stdErr)
        if medianErr < self.tol and stdErr < self.tol:
            print('The errors are within the target %d percent %%' % self.tol)
            
        # print('100% done')
        recID = recID.tolist()
        # Add selected record information to self
        self.rec_scale = finalScaleFac
        self.rec_spec = sampleSmall
        self.rec_Vs30 = Vs30[recID]
        self.rec_Rjb = Rjb[recID]
        self.rec_Mw = Mw[recID]
        self.rec_fault = fault[recID]
        self.rec_h1 = Filename_1[recID]
        
        if self.selection == 1:
            self.rec_h2 = None
        elif self.selection == 2:
            self.rec_h2 = Filename_2[recID]

        if self.database['Name'] == 'NGA_W2':
            self.rec_rsn = NGA_num[recID]
        else:
            self.rec_rsn = None
            
    def write(self, cs = 0, recs = 1):
        
        if recs == 1:
            # set the directories and file names
            zipName = 'Records.zip'
            n = len(self.rec_h1)
            path_dts = os.path.join(self.outdir,'GMR_dts.txt')
            path_durs = os.path.join(self.outdir,'GMR_durs.txt')
            dts = np.zeros((n))
            durs = np.zeros((n))

            if not self.rec_h2 is None:
                path_H1 = os.path.join(self.outdir,'GMR_H1_names.txt')
                path_H2 = os.path.join(self.outdir,'GMR_H2_names.txt')
                h2s = open(path_H2, 'w')
            else:
                path_H1 = os.path.join(self.outdir,'GMR_names.txt')
            h1s = open(path_H1, 'w')            
            if self.database['Name'] == 'NGA_W1':
    
                # save the first gm components
                for i in range(n):
                    rec_path = self.database['Name']+'/'+self.rec_h1[i][:-3] + 'at2'
                    dts[i], _, _, t, inp_acc = ReadNGA(rec_path,zipName)
                    durs[i] = t[-1]
                    gmr_file = 'GMR_'+str(i+1)+'.txt'
                    path = os.path.join(self.outdir,gmr_file)
                    acc_Sc = self.rec_scale[i] * inp_acc
                    np.savetxt(path, acc_Sc, fmt='%1.4e')
                    h1s.write(gmr_file+'\n')
                
                h1s.close()
                np.savetxt(path_dts,dts, fmt='%1.4e')
                np.savetxt(path_durs,durs, fmt='%1.4e')
                
                # save the second gm components
                if not self.rec_h2 is None:
                    for i in range(n):
                        rec_path = self.database['Name']+'/'+self.rec_h2[i][:-3] + 'at2'
                        _, _, _, _, inp_acc = ReadNGA(rec_path,zipName)
                        gmr_file = 'GMR_'+str(n+i+1)+'.txt'
                        path = os.path.join(self.outdir,gmr_file)
                        acc_Sc = self.rec_scale[i] * inp_acc
                        np.savetxt(path, acc_Sc, fmt='%1.4e')
                        h2s.write(gmr_file+'\n')                
                    
                    h2s.close()
    
            if self.database['Name'].startswith('EXSIM'):
                sf = 1/981 # cm/s**2 to g
                for i in range(n):
                    temp = self.rec_h1[i].split('_acc')[0]
                    rec_path = self.database['Name']+'/'+temp+'/'+self.rec_h1[i]
                    dts[i], _, _, t, inp_acc = ReadEXSIM(rec_path,zipName)
                    durs[i] = t[-1]
                    gmr_file = 'GMR_'+str(i+1)+'.txt'
                    path = os.path.join(self.outdir,gmr_file)
                    acc_Sc = self.rec_scale[i] * inp_acc * sf
                    np.savetxt(path, acc_Sc, fmt='%1.4e')
                    h1s.write(gmr_file+'\n')
                    
                h1s.close()
                np.savetxt(path_dts,dts, fmt='%1.4e')
                np.savetxt(path_durs,durs, fmt='%1.4e')
            
        if cs == 1:
            # save some info as pickle obj
            path_cs = os.path.join(self.outdir,'CS.pkl')  
            cs_obj = vars(copy.deepcopy(self)) # use copy.deepcopy to create independent obj
            cs_obj['database'] = self.database['Name']
            cs_obj['gmpe'] = str(cs_obj['bgmpe']).replace('[','',).replace(']','')
            del cs_obj['bgmpe'] 
            del cs_obj['outdir']
            with open(path_cs, 'wb') as file:
                pickle.dump(cs_obj, file)
        
        print('Finished writing process, the files are located in %s' % self.outdir)

    def nga_download(self, username , pwd):
        """
        
        Details
        -------
        
        This function has been created as a web automation tool in order to 
        download unscaled record time histories from NGA-West2 Database 
        (https://ngawest2.berkeley.edu/) by Record Sequence Numbers (RSNs).

        Parameters
        ----------
        username     : str
                Account username (e-mail)
                            e.g.: 'username@mail.com'
        pwd          : str
                Account password
                            e.g.: 'password!12345'

        """
        self.username = username
        self.pwd = pwd

        def download_url(url, save_path, chunk_size=128):
            """
            
            Details
            -------
            
            This function downloads file from given url.Herein, it is being used 

            Parameters
            ----------
            url          : str
                    e.g.: 'www.example.com/example_file.pdf'
            save_path    : str
                    Save directory.

            """
            r = requests.get(url, stream=True)
            with open(save_path, 'wb') as fd:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    fd.write(chunk)     

        def find_latest_ver():
            """
            
            Details
            -------
            
            This function finds the latest version of the chrome driver from  
            'https://chromedriver.chromium.org/'.

            """
            r = requests.get('https://chromedriver.chromium.org/')
            a = r.text
            start = a.find('Latest stable release:')
            text = a.replace(a[0:start],'')
            start = text.find('path=')      

            text = text.replace(text[0:start+5],'')
            end = text.find("/")
            latest_ver = text.replace(text[end::],'')
            return latest_ver       

        def add_driver_to_the_PATH(save_path):
            paths = sys.path
            package = [i for i in paths if 'lib' in i][0]
            with zipfile.ZipFile(save_path, 'r') as zip_ref:
                zip_ref.extractall(package)

        def dir_size(Down_Dir):
            total_size = 0
            for path, dirs, files in os.walk(Down_Dir):
                for f in files:
                    fp = os.path.join(path, f)
                    total_size += os.path.getsize(fp)
            return total_size       

        def download_wait(Down_Dir):
            delta_size = 100
            flag = 0
            flag_lim = 5
            while delta_size > 0 and flag < flag_lim:
                print
                size_0 = dir_size(Down_Dir)
                sleep(6)
                size_1 = dir_size(Down_Dir)
                if size_1-size_0 > 0:
                    delta_size = size_1-size_0
                else:
                    flag += 1
                    print(flag_lim-flag)
            print(f'Download has done to the directory:\n{Down_Dir}')          

        def seek_and_download():
            """
            
            Details
            -------
            
            This function finds the latest version of the chrome driver from  
            'https://chromedriver.chromium.org/' and downloads the compatible
            version to the OS and extract it to the path.

            """
            paths = sys.path
            package = [i for i in paths if 'lib' in i][0]
            if 'win' in sys.platform:
                current_platform = 'win32'
                aim_driver = 'chromedriver.exe'
            elif 'linux' in sys.platform:
                current_platform = 'linux64'
                aim_driver = 'chromedriver'
            else:       
                current_platform = 'mac64'
                aim_driver = 'chromedriver'
            if aim_driver not in os.listdir(package):
                latest_ver = find_latest_ver()
                save_path = os.path.join(os.getcwd(),'chromedriver.zip')
                url = f"https://chromedriver.storage.googleapis.com/{latest_ver}/chromedriver_{current_platform}.zip"
                download_url(url, save_path, chunk_size=128)
                add_driver_to_the_PATH(save_path)
                print ('chromedriver downloaded successfully!!')
                os.remove(save_path)
            else:
                print("chromedriver allready exists!!")

        def go_to_sign_in_page(Download_Dir):
            """
            
            Details
            -------
            
            This function starts the webdriver in headless mode and 
            opens the sign in page to 'https://ngawest2.berkeley.edu/'

            Parameters
            ----------
            Download_Dir     : str
                    Directory for the output time histories to be downloaded

            """

            ChromeOptions = webdriver.ChromeOptions()
            prefs = {"download.default_directory" : Download_Dir}
            ChromeOptions.add_experimental_option("prefs",prefs)
            ChromeOptions.headless = True
            if 'win' in sys.platform:
                aim_driver = 'chromedriver.exe'
            elif 'linux' in sys.platform:
                aim_driver = 'chromedriver'
            else:       
                aim_driver = 'chromedriver'
            path_of_driver = os.path.join([i for i in sys.path if 'lib' in i][0] , aim_driver)
            if not os.path.exists(path_of_driver):
                print('Downloading the chromedriver!!')
                seek_and_download()
            driver = webdriver.Chrome(executable_path = path_of_driver ,options=ChromeOptions)
            url_sign_in = 'https://ngawest2.berkeley.edu/users/sign_in'
            driver.get(url_sign_in)
            return driver       

        def sign_in_with_given_creds(driver,USERNAME,PASSWORD):
            """
            
            Details
            -------
            
            This function signs in to 'https://ngawest2.berkeley.edu/' with
            given account credentials

            Parameters
            ----------
            driver     : selenium webdriver object
                    Please use the driver have been generated as output of 
                    'go_to_sign_in_page' function
            USERNAME   : str
                    Account username (e-mail)
                                e.g.: 'username@mail.com'
            PASSWORD   : str
                    Account password
                                e.g.: 'password!12345' 
            """
            print("Signing in with given account!...")
            driver.find_element_by_id('user_email').send_keys(USERNAME)
            driver.find_element_by_id('user_password').send_keys(PASSWORD)
            driver.find_element_by_id('user_submit').click()
            try:
                alert = driver.find_element_by_css_selector('p.alert')
                warn = alert.text
                print(warn)
            except:
                warn = ''
                pass
            return driver, warn     

        def Download_Given(RSNs,Download_Dir,driver):
            """
            
            Details
            -------
            
            This function dowloads the timehistories which have been indicated with their RSNs
            from 'https://ngawest2.berkeley.edu/'.

            Parameters
            ----------
            RSNs     : str
                    A string variable contains RSNs to be downloaded which uses ',' as delimeter
                    between RNSs
                                e.g.: '1,5,91,35,468'
            Download_Dir     : str
                    Directory for the output timehistories to be downloaded
            driver     : selenium webdriver object
                    Please use the driver have been generated as output of 
                    sign_in_with_given_creds' function

            """
            url_get_record = 'https://ngawest2.berkeley.edu/spectras/new?sourceDb_flag=1'   
            print("Listing the Records!....")
            driver.get(url_get_record)
            driver.find_element_by_xpath("//button[@type='button']").submit()
            sleep(2)
            driver.find_element_by_id('search_search_nga_number').send_keys(RSNs)
            sleep(3)
            driver.find_element_by_xpath("//button[@type='button' and @onclick='uncheck_plot_selected();reset_selectedResult();OnSubmit();']").submit()
            try:
                note = driver.find_element_by_id('notice').text 
            except:
                note = 'NO'

            if 'NO' in note:
                driver.quit()
                pass
            else:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                sleep(3)
                driver.find_element_by_xpath("//button[@type='button' and @onclick='getSelectedResult(true)']").click()
                print("Downloading the Records!...")
                obj = driver.switch_to.alert
                msg=obj.text
                print ("Alert shows following message: "+ msg )
                sleep(5)
                obj.accept()       
                obj = driver.switch_to.alert
                msg=obj.text
                print ("Alert shows following message: "+ msg )
                sleep(3)
                obj.accept()
                print("Downloading the Records!...")  
                download_wait(Download_Dir)
                driver.quit()

        driver = go_to_sign_in_page(self.outdir)
        driver,warn = sign_in_with_given_creds(driver,self.username,self.pwd)
        if str(warn) == 'Invalid email or password.':
            print(warn)
            driver.quit()
            sys.exit()
        else:
            RSNs = ''
            for i in self.rec_rsn:
                RSNs += str(int(i)) + ','

            RSNs = RSNs[:-1:]
            print(RSNs)
            files_before_download = set(os.listdir(self.outdir))
            Download_Given(RSNs,self.outdir,driver)
            files_after_download = set(os.listdir(self.outdir))
            Downloaded_File = str(list(files_after_download.difference(files_before_download))[0])
            file_extension = Downloaded_File[Downloaded_File.find('.')::]
            file_name = Downloaded_File[:Downloaded_File.find('.'):]
            time_tag = gmtime()
            time_tag_str = f'{time_tag[0]}'
            for i in range(1,len(time_tag)):
                time_tag_str += f'_{time_tag[i]}'
            new_file_name = f'unscaled_records_{time_tag_str}{file_extension}'
            Downloaded_File = os.path.join(self.outdir,Downloaded_File)
            Downloaded_File_Rename = os.path.join(self.outdir,new_file_name)
            os.rename(Downloaded_File,Downloaded_File_Rename)
            self.Unscaled_rec_file = Downloaded_File_Rename



        
    def plot(self, cs = 0, sim = 0, rec = 1, save = 0):
        """
        
        Details
        -------
        Plots the conditional spectrum and spectra 
        of selected simulations and records.

        Parameters
        ----------
        cs     : int, optional
            Flag to plot conditional spectrum.
            The default is 1.
        sim    : int, optional
            Flag to plot simulated response spectra vs. conditional spectrum.
            The default is 0.
        rec    : int, optional
            Flag to plot Selected response spectra of selected records
            vs. conditional spectrum. 
            The default is 1.
        save   : int, optional
            Flag to save plotted figures in pdf format.
            The default is 0.
        outdir : str, optional
            Output directory to save plots.
            The default is 'Outputs'.
            
        Notes
        -----
        0: no, 1: yes

        Returns
        -------
        None.

        """

        SMALL_SIZE = 10
        MEDIUM_SIZE = 12
        BIG_SIZE = 14
        BIGGER_SIZE = 18
        
        plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
        plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
        plt.rc('axes', labelsize=BIG_SIZE)       # fontsize of the x and y labels
        plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
        plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
        plt.rc('legend', fontsize=MEDIUM_SIZE)   # legend fontsize
        plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title
        plt.ioff()

        if self.cond == 1:
            if len(self.Tstar) == 1:
                hatch = [self.Tstar*0.98, self.Tstar*1.02]
            else:
                hatch = [self.Tstar.min(), self.Tstar.max()]

        if cs == 1:
            # Plot Target spectrum vs. Simulated response spectra
            fig,ax = plt.subplots(1,2, figsize = (16,8))
            plt.suptitle('Target Spectrum', y = 0.95)
            ax[0].loglog(self.T,np.exp(self.mu_ln),color = 'red', lw=2, label='Target - $e^{\mu_{ln}}$')
            if self.useVar == 1:
                ax[0].loglog(self.T,np.exp(self.mu_ln+2*self.sigma_ln),color = 'red', linestyle='--', lw=2, label='Target - $e^{\mu_{ln}\mp 2\sigma_{ln}}$')
                ax[0].loglog(self.T,np.exp(self.mu_ln-2*self.sigma_ln),color = 'red', linestyle='--', lw=2, label='Target - $e^{\mu_{ln}\mp 2\sigma_{ln}}$')
            
            ax[0].get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
            ax[0].set_xticks([0.1, 0.2, 0.5, 1, 2, 3, 4])
            ax[0].get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
            ax[0].set_yticks([0.1, 0.2, 0.5, 1, 2, 3, 4, 5])
            ax[0].set_xlabel('Period [sec]')
            ax[0].set_ylabel('Spectral Acceleration [g]')
            ax[0].grid(True)
            handles, labels = ax[0].get_legend_handles_labels()
            by_label = dict(zip(labels, handles))
            ax[0].legend(by_label.values(), by_label.keys(), frameon = False)
            ax[0].set_xlim([self.T[0],self.T[-1]])
            if self.cond == 1:
                ax[0].axvspan(hatch[0], hatch[1], facecolor='red', alpha=0.3)
                   
            # Sample and target standard deviations
            if self.useVar == 1:
                ax[1].semilogx(self.T,self.sigma_ln,color = 'red', linestyle='--', lw=2, label='Target - $\sigma_{ln}$')
                ax[1].set_xlabel('Period [sec]')
                ax[1].set_ylabel('Dispersion')
                ax[1].grid(True)
                ax[1].legend(frameon = False)
                ax[1].get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
                ax[1].set_xticks([0.1, 0.2, 0.5, 1, 2, 3, 4])
                ax[1].get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
                ax[0].set_xlim([self.T[0],self.T[-1]])
                ax[1].set_ylim(bottom=0)
                if self.cond == 1:
                    ax[1].axvspan(hatch[0], hatch[1], facecolor='red', alpha=0.3)
            plt.show()
            
            if save == 1:
                plt.savefig(os.path.join(self.outdir,'Targeted.pdf'))

        if sim == 1:
            # Plot Target spectrum vs. Simulated response spectra
            fig,ax = plt.subplots(1,2, figsize = (16,8))
            plt.suptitle('Target Spectrum vs. Simulated Spectra', y = 0.95)
            ax[0].loglog(self.T,np.exp(self.mu_ln),color = 'red', lw=2, label='Target - $e^{\mu_{ln}}$')
            if self.useVar == 1:
                ax[0].loglog(self.T,np.exp(self.mu_ln+2*self.sigma_ln),color = 'red', linestyle='--', lw=2, label='Target - $e^{\mu_{ln}\mp 2\sigma_{ln}}$')
                ax[0].loglog(self.T,np.exp(self.mu_ln-2*self.sigma_ln),color = 'red', linestyle='--', lw=2, label='Target - $e^{\mu_{ln}\mp 2\sigma_{ln}}$')

            ax[0].loglog(self.T,np.exp(np.mean(self.sim_spec,axis=0)),color = 'blue', lw=2, label='Selected - $e^{\mu_{ln}}$')
            if self.useVar == 1:
                ax[0].loglog(self.T,np.exp(np.mean(self.sim_spec,axis=0)+2*np.std(self.sim_spec,axis=0)),color = 'blue', linestyle='--', lw=2, label='Selected - $e^{\mu_{ln}\mp 2\sigma_{ln}}$')
                ax[0].loglog(self.T,np.exp(np.mean(self.sim_spec,axis=0)-2*np.std(self.sim_spec,axis=0)),color = 'blue', linestyle='--', lw=2, label='Selected - $e^{\mu_{ln}\mp 2\sigma_{ln}}$')
                        
            for i in range(self.nGM):
                ax[0].loglog(self.T,np.exp(self.sim_spec[i,:]),color = 'gray', lw=1,label='Selected');
            
            ax[0].get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
            ax[0].set_xticks([0.1, 0.2, 0.5, 1, 2, 3, 4])
            ax[0].get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
            ax[0].set_yticks([0.1, 0.2, 0.5, 1, 2, 3, 4, 5])
            ax[0].set_xlabel('Period [sec]')
            ax[0].set_ylabel('Spectral Acceleration [g]')
            ax[0].grid(True)
            handles, labels = ax[0].get_legend_handles_labels()
            by_label = dict(zip(labels, handles))
            ax[0].legend(by_label.values(), by_label.keys(), frameon = False)
            ax[0].set_xlim([self.T[0],self.T[-1]])
            if self.cond == 1:
                ax[0].axvspan(hatch[0], hatch[1], facecolor='red', alpha=0.3)

            if self.useVar == 1:
                # Sample and target standard deviations
                ax[1].semilogx(self.T,self.sigma_ln,color = 'red', linestyle='--', lw=2, label='Target - $\sigma_{ln}$')
                ax[1].semilogx(self.T,np.std(self.sim_spec,axis=0),color = 'black', linestyle='--', lw=2, label='Selected - $\sigma_{ln}$')
                ax[1].set_xlabel('Period [sec]')
                ax[1].set_ylabel('Dispersion')
                ax[1].grid(True)
                ax[1].legend(frameon = False)
                ax[1].get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
                ax[1].set_xticks([0.1, 0.2, 0.5, 1, 2, 3, 4])
                ax[1].get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
                ax[1].set_xlim([self.T[0],self.T[-1]])
                ax[1].set_ylim(bottom=0)
                if self.cond == 1:
                    ax[1].axvspan(hatch[0], hatch[1], facecolor='red', alpha=0.3)
                plt.show()
            
            if save == 1:
                plt.savefig(os.path.join(self.outdir,'Simulated.pdf'))
            
        if rec == 1:
            # Plot Target spectrum vs. Selected response spectra
            fig,ax = plt.subplots(1,2, figsize = (16,8))
            plt.suptitle('Target Spectrum vs. Spectra of Selected Records', y = 0.95)
            ax[0].loglog(self.T,np.exp(self.mu_ln),color = 'red', lw=2, label='Target - $e^{\mu_{ln}}$')
            if self.useVar == 1:
                ax[0].loglog(self.T,np.exp(self.mu_ln+2*self.sigma_ln),color = 'red', linestyle='--', lw=2, label='Target - $e^{\mu_{ln}\mp 2\sigma_{ln}}$')
                ax[0].loglog(self.T,np.exp(self.mu_ln-2*self.sigma_ln),color = 'red', linestyle='--', lw=2, label='Target - $e^{\mu_{ln}\mp 2\sigma_{ln}}$')

            ax[0].loglog(self.T,np.exp(np.mean(self.rec_spec,axis=0)),color = 'blue', lw=2, label='Selected - $e^{\mu_{ln}}$')
            ax[0].loglog(self.T,np.exp(np.mean(self.rec_spec,axis=0)+2*np.std(self.rec_spec,axis=0)),color = 'blue', linestyle='--', lw=2, label='Selected - $e^{\mu_{ln}\mp 2\sigma_{ln}}$')
            ax[0].loglog(self.T,np.exp(np.mean(self.rec_spec,axis=0)-2*np.std(self.rec_spec,axis=0)),color = 'blue', linestyle='--', lw=2, label='Selected - $e^{\mu_{ln}\mp 2\sigma_{ln}}$')

            for i in range(self.nGM):
                ax[0].loglog(self.T,np.exp(self.rec_spec[i,:]),color = 'gray', lw=1,label='Selected');
            
            ax[0].get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
            ax[0].set_xticks([0.1, 0.2, 0.5, 1, 2, 3, 4])
            ax[0].get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
            ax[0].set_yticks([0.1, 0.2, 0.5, 1, 2, 3, 4, 5])
            ax[0].set_xlabel('Period [sec]')
            ax[0].set_ylabel('Spectral Acceleration [g]')
            ax[0].grid(True)
            handles, labels = ax[0].get_legend_handles_labels()
            by_label = dict(zip(labels, handles))
            ax[0].legend(by_label.values(), by_label.keys(), frameon = False)
            ax[0].set_xlim([self.T[0],self.T[-1]])
            if self.cond == 1:
                ax[0].axvspan(hatch[0], hatch[1], facecolor='red', alpha=0.3)
                   
            # Sample and target standard deviations
            ax[1].semilogx(self.T,self.sigma_ln,color = 'red', linestyle='--', lw=2, label='Target - $\sigma_{ln}$')
            ax[1].semilogx(self.T,np.std(self.rec_spec,axis=0),color = 'black', linestyle='--', lw=2, label='Selected - $\sigma_{ln}$')
            ax[1].set_xlabel('Period [sec]')
            ax[1].set_ylabel('Dispersion')
            ax[1].grid(True)
            ax[1].legend(frameon = False)
            ax[1].get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
            ax[1].set_xticks([0.1, 0.2, 0.5, 1, 2, 3, 4])
            ax[0].set_xlim([self.T[0],self.T[-1]])
            ax[1].get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
            ax[1].set_ylim(bottom=0)
            if self.cond == 1:
                ax[1].axvspan(hatch[0], hatch[1], facecolor='red', alpha=0.3)
            plt.show()
            
            if save == 1:
                plt.savefig(os.path.join(self.outdir,'Selected.pdf'))

def Baker_Jayaram_2008(T1, T2):
    """
    
    Details
    -------
    Compute the inter-period correlation for any two Sa(T) values

    References
    ----------
    Baker JW, Jayaram N. Correlation of Spectral Acceleration Values from NGA Ground Motion Models.
    Earthquake Spectra 2008; 24(1): 299–317. DOI: 10.1193/1.2857544.

    Parameters
    ----------
        T1: int
            First period
        T2: int
            Second period

    Returns
    -------
    rho: int
         Predicted correlation coefficient

    """

    t_min = min(T1, T2)
    t_max = max(T1, T2)

    c1 = 1.0 - np.cos(np.pi / 2.0 - np.log(t_max / max(t_min, 0.109)) * 0.366)

    if t_max < 0.2:
        c2 = 1.0 - 0.105 * (1.0 - 1.0 / (1.0 + np.exp(100.0 * t_max - 5.0))) * (t_max - t_min) / (t_max - 0.0099)
    else:
        c2 = 0

    if t_max < 0.109:
        c3 = c2
    else:
        c3 = c1

    c4 = c1 + 0.5 * (np.sqrt(c3) - c3) * (1.0 + np.cos(np.pi * t_min / 0.109))

    if t_max <= 0.109:
        rho = c2
    elif t_min > 0.109:
        rho = c1
    elif t_max < 0.2:
        rho = min(c2, c4)
    else:
        rho = c4

    return rho

def Sa_avg(bgmpe,scenario,T):
    """

    Details
    -------
    GMPM of average spectral acceleration
    The code will get as input the selected periods, 
    Magnitude, distance and all other parameters of the 
    selected GMPM and 
    will return the median and logarithmic Spectral 
    acceleration of the product of the Spectral
    accelerations at selected periods; 

    Parameters
    ----------
    bgmpe : openquake object
        the openquake gmpe object.
    scenario : list
        [sites, rup, dists] source, distance and site context 
        of openquake gmpe object for the specified scenario.
    T : numpy.ndarray
        Array of interested Periods (sec).

    Returns
    -------
    Sa : numpy.ndarray
        Mean of logarithmic average spectral acceleration prediction.
    sigma : numpy.ndarray
       logarithmic standard deviation of average spectral acceleration prediction.

    """
    
    n = len(T);
    mu_lnSaTstar = np.zeros(n)
    sigma_lnSaTstar = np.zeros(n)
    MoC = np.zeros((n,n))
    # Get the GMPE output
    for i in range(n):
        mu_lnSaTstar[i], stddvs_lnSaTstar = bgmpe.get_mean_and_stddevs(scenario[0], scenario[1], scenario[2], imt.SA(period=T[i]),[const.StdDev.TOTAL])
        # convert to sigma_arb
        # One should uncomment this line if the arbitary component is used for
        # record selection.
        # ro_xy = 0.79-0.23*np.log(T[k])
        ro_xy = 1
        sigma_lnSaTstar[i] = np.log(((np.exp(stddvs_lnSaTstar[0][0])**2)*(2/(1+ro_xy)))**0.5)
        
        for j in range(n):
            rho = Baker_Jayaram_2008(T[i], T[j])
            MoC [i,j] = rho

    SPa_avg_meanLn = (1/n) *sum(mu_lnSaTstar) # logarithmic mean of Sa,avg

    SPa_avg_std = 0
    for i in range(n):
        for j in range(n):
            SPa_avg_std = SPa_avg_std  + (MoC[i,j] *sigma_lnSaTstar[i]*sigma_lnSaTstar[j]) # logarithmic Var of the Sa,avg

    SPa_avg_std = SPa_avg_std*(1/n)**2
    # compute mean of logarithmic average spectral acceleration
    # and logarithmic standard deviation of 
    # spectral acceleration prediction
    Sa    = SPa_avg_meanLn
    sigma = np.sqrt(SPa_avg_std)
    return Sa, sigma

def rho_AvgSA_SA(bgmpe,scenario,T,Tstar):
    """
    Details
    -------  
    function to compute the correlation between Spectra acceleration and AvgSA.
    
    Parameters
    ----------
    bgmpe : openquake object
        the openquake gmpe object.
    scenario : list
        [sites, rup, dists] source, distance and site context 
        of openquake gmpe object for the specified scenario.
    T     : numpy.ndarray
        Array of interested Periods to calculate correlation coefficient.

    Tstar : numpy.ndarray
        Period range where AvgSa is calculated.

    Returns
    -------
    rho : int
        Predicted correlation coefficient.

    """
    
    rho=0
    for j in range(len(Tstar)):
        rho_bj = Baker_Jayaram_2008(T, Tstar[j])
        _, sig1 = bgmpe.get_mean_and_stddevs(scenario[0], scenario[1], scenario[2], imt.SA(period=Tstar[j]),[const.StdDev.TOTAL])
        rho = rho_bj*sig1[0][0] + rho

    _, Avg_sig = Sa_avg(bgmpe,scenario,Tstar)
    rho = rho/(len(Tstar)*Avg_sig)
    return rho

def get_RotDxx(Sa_1, Sa_2, xx, num_theta = 100):
    """
    
    Details
    -------
    Compute the RoTDxx IM of a pain of spectral quantities.
    
    References
    ----------
    Boore DM. Orientation-independent, nongeometric-mean measures of seismic
    intensity from two horizontal components of motion. Bulletin of the
    Seismological Society of America 2010; 100(4): 1830–1835.
    DOI: 10.1785/0120090400.

    Parameters
    ----------
    Sa_1 : numpy.ndarray
        Spectral acceleration values in direction 1.
    Sa_2 : numpy.ndarray
        Spectral acceleration values in direction 2.
    xx : int
        Value of RoTDxx to compute.
    num_theta : int, optional
        Number of rotations to consider between 0 and 180°. The default is 100.

    Returns
    -------
    RotDxx : numpy.ndarray
        Value of IM.

    """
    nGM, nT = Sa_1.shape
    theta = np.linspace(start=0, stop=np.pi, num=num_theta)

    Rot = np.zeros((num_theta, nT))
    RotDxx = np.zeros((nGM,nT))
    for i in range(nGM):
        for j in range(num_theta):
            Rot[j,:] = Sa_1[i,:]*np.cos(theta[j])+Sa_2[i,:]*np.sin(theta[j])
        
        RotDxx[i,:] = np.percentile(Rot,xx,axis=0)

    return RotDxx

def ReadNGA(inFilename, zipName=None, outFilename=None):
    """
    
    Details
    -------
    This function process acceleration history for NGA data file (.AT2 format).
    
    Parameters
    ----------
    inFilename : str
        location and name of the input file.
    zipName    : str
        it is assumed that the database is located in this file.
    outFilename : str, optional
        location and name of the output file. 
        The default is None.

    Returns
    -------
    dt : float
        time interval of recorded points.
    npts : int
        number of points in ground motion record file.
    desc : str
        Description of the earthquake (e.g., name, year, etc).
    t    : numpy.array (n x 1)
        time array, same length with npts.
    acc  : numpy.array (n x 1)
        acceleration array, same length with time unit 
        usually in (g) unless stated as other.

    """

    try:
        # Read the ground motion from zipped database folder
        if not zipName is None:
            with zipfile.ZipFile(zipName, 'r') as myzip:
                with myzip.open(inFilename) as myfile:
                    content = [x.decode('utf-8') for x in myfile.readlines()]
                    
        # Read the ground motion from unzipped database folder
        else:
            with open(inFilename,'r') as inFileID:
                content = inFileID.readlines()
        
        # check the first line
        temp = str(content[0]).split()
        try:
            # description is in the end
            float(temp[0])
            flag = 1
        except:
            # description is in the begining
            flag = 0
        
        counter = 0
        desc, row4Val, acc_data = "","",[]
                
        if flag == 1:
            for x in content:
                if counter == len(content)-3:
                    desc = x
                elif counter == len(content)-1:
                    row4Val = x
                    if row4Val[0][0] == 'N':
                        val = row4Val.split()
                        npts = float(val[(val.index('NPTS='))+1].rstrip(','))
                        dt = float(val[(val.index('DT='))+1])
                    else:
                        val = row4Val.split()
                        npts = float(val[0])
                        dt = float(val[1])
                        
                elif counter < len(content)-4:
                    data = str(x).split()
                    for value in data:
                        a = float(value)
                        acc_data.append(a)
                    acc = np.asarray(acc_data)
                counter = counter + 1

        if flag == 0:
            for x in content:
                if counter == 1:
                    desc = x
                elif counter == 3:
                    row4Val = x
                    if row4Val[0][0] == 'N':
                        val = row4Val.split()
                        npts = float(val[(val.index('NPTS='))+1].rstrip(','))
                        dt = float(val[(val.index('DT='))+1])
                    else:
                        val = row4Val.split()
                        npts = float(val[0])
                        dt = float(val[1])
                        
                elif counter > 3:
                    data = str(x).split()
                    for value in data:
                        a = float(value)
                        acc_data.append(a)
                    acc = np.asarray(acc_data)
                counter = counter + 1
            
        t = [] # save time history
        for i in range (0,len(acc_data)):
            ti = i * dt
            t.append(ti)
            
        if outFilename is not None:
            np.savetxt(outFilename, acc, fmt='%1.4e')

        npts = int(npts)
        return dt, npts, desc, t, acc
    
    except IOError:
        print("processMotion FAILED!: The record file is not in the directory")

def ReadEXSIM(inFilename, zipName=None, outFilename=None):
    """
    
    Details
    -------
    This function process acceleration history for EXSIM data file.
    
    Parameters
    ----------
    inFilename : str
        location and name of the input file.
    zipName    : str
        it is assumed that the database is located in this file.
    outFilename : str, optional
        location and name of the output file. 
        The default is None.

    Returns
    -------
    dt   : float
        time interval of recorded points.
    npts : int
        number of points in ground motion record file.
    desc : str
        Description of the earthquake (e.g., name, year, etc).
    time : numpy.array (n x 1)
        time array, same length with npts.
    acc  : numpy.array (n x 1)
        acceleration array, same length with time unit 
        usually in (g) unless stated as other.

    """
    
    try:
        # Read the ground motion from zipped database folder
        if not zipName is None:
            with zipfile.ZipFile(zipName, 'r') as myzip:
                with myzip.open(inFilename) as myfile:
                    content = [x.decode('utf-8') for x in myfile.readlines()]
                    
        # Read the ground motion from unzipped database folder
        else:
            with open(inFilename,'r') as inFileID:
                content = inFileID.readlines()
    
        desc = content[:12]
        dt = float(content[6].split()[1])
        npts = int(content[5].split()[0])
        acc = []
        t = []
        
        for i in range(12,len(content)):
            temp = content[i].split()
            acc.append(float(temp[1]))
        
        acc = np.asarray(acc)
        if len(acc) < 20000:
            acc = acc[2500:10800] # get rid of zeros
        dur = len(acc)*dt
        t = np.arange(0,dur,dt)

        if outFilename is not None:
            np.savetxt(outFilename, acc, fmt='%1.4e')

        return dt, npts, desc, t, acc
    
    except IOError:
        print("processMotion FAILED!: The record file is not in the directory")
    
def create_outdir(outdir_path):
    """  

    Parameters
    ----------
    outdir_path : str
        output directory to create.

    Returns
    -------
    None.

    """
    shutil.rmtree(outdir_path, ignore_errors=True)
    os.makedirs(outdir_path)
    
def RunTime():
    """

    Details
    -------
    Prints the time passed between startTime and Finishtime (now)
    in hours, minutes, seconds. startTime is a global variable.

    Parameters
    ----------
    None.

    Returns
    -------
    None.

    """
    finishTime = time()
    # Procedure to obtained elapsed time in Hr, Min, and Sec
    timeSeconds = finishTime-startTime
    timeMinutes = int(timeSeconds/60);
    timeHours = int(timeSeconds/3600);
    timeMinutes = int(timeMinutes - timeHours*60)
    timeSeconds = timeSeconds - timeMinutes*60 - timeHours*3600
    print("Run time: %d hours: %d minutes: %.2f seconds"  % (timeHours, timeMinutes, timeSeconds))
