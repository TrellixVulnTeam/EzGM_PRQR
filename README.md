# EzGM
Toolbox for ground motion record selection and processing. 

[![DOI](https://zenodo.org/badge/291944652.svg)](https://zenodo.org/badge/latestdoi/291944652) 

***
## Getting Started
```
import EzGM
```
The package has three different modules: 
1. **EzGM.selection** deals with the record selection. 
   It can be used to perform unconditional or conditional spectrum based selection in which intensity measure can be chosen as Sa(T*) or AvgSa(T*). The tool makes use of 
   [OpenQuake hazard library](https://docs.openquake.org/oq-engine/3.14/openquake.hazardlib.gsim.html#ground-shaking-intensity-models) and 
   thus any available ground motion prediction equation available can directly be used (see Example 1). <br />
   It can also be used to perform the selection based on Turkish Building Earthquake Code, TBEC-2018, ASCE 7-16, and Eurocode 8 Part 1 (see Example 2). <br />
   Currently, the records can be selected from the two publicly available databases: *NGA_W2* and *ESM_2018*. 
   The original flat-files for these databases were modified by discarding the records which are not possible to download. <br />
   The database files which include features to perform record selection are stored as .mat files in path/to/EzGM/Meta_Data.
   If the user desires to use/add another database such as ESM_2018.mat, s/he must stick to the same format in publicly available databases. <br />
   Upon performing ground motion record selection/scaling if user desires to get formatted records, for the given metadata, s/he should place the available records from metadata file into the Records.zip with the name of database, 
   e.g. *ESM_2018.zip* for database *ESM_2018*. 
   <br /> In case of publicly available databases, the user can also download the records directly by using the associated methods since the records are not generally available beforehand.
   To use *ESM_2018* database, the user must have access token (path/to/current/directory/token.txt) from https://esm-db.eu. The token
   can be retrieved using EzGM as well (see Example 1). In order to use *NGA_W2* database, user must have account obtained from https://ngawest2.berkeley.edu.
2. **EzGM.utility** can be used to post-process results of probabilistic seismic hazard analysis (PSHA) from OpenQuake.Engine. Its methods can be used to read and visualize seismic hazard curves and seismic disaggregation results. The module can be particularly useful
while performing conditional spectrum (CS) based record selection for multiple-stripe analysis (MSA) (see Example 3).
3. **EzGM.signal** can be used to process ground motion records. It contains methods for filtering, baseline correction, and intensity measure calculations (see Example 4).

At the moment, no documentation is available for EzGM; hence, users are recommended to see the jupyter notebook examples to get familiar with EzGM.
These can be accessed and run through *binder* which is an online service to deploy interactive computational environments for online repositories.
For EzGM examples, see:

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/volkanozsarac/EzGM/HEAD?filepath=Examples%2Fbinder)
***
## Installation
- EzGM downloads google-chrome or firefox webdriver while executing ngaw2_download method. Therefore, user-specified browser ('chrome' or 'firefox') must be readily available.
- EzGM requires several other packages: <br /> openquake.engine>=3.14.0; numba==0.55.1; selenium==4.1.3; beautifulsoup4==4.11.1; tqdm==4.64.0; h5py==3.1.0; matplotlib==3.1.2
- The package management system *pip* can be used to install EzGM (python >=3.7, <3.9).
- In order to avoid any potential issues, the following is recommended for installation:
   1. First, upgrade pip.
   ```
   pip install --upgrade pip --user
   ```
   2. Then, retrieve the universal installer from https://github.com/gem/oq-engine and install the required packages for you operating system via one of the followings.
   ```
   pip install -r requirements_py38macos.txt
   pip install -r requirements_py38win64.txt
   pip install -r requirements_py38linux64.txt
   ```
   3. Then, use the universal installer to install openquake.engine.
   ```
   python setup.py install
   ```
   4. Finally, install EzGM via pip.
   ```
   pip install EzGM
   ```
***
## Acknowledgements
Special thanks to Besim Yukselen for his help in the development of ngaw2_download method, and Gerard J. O'Reilly for sharing his knowledge in the field with me. The EzGM.selection.conditional_spectrum method is greatly inspired by Prof. Jack W. Baker whom I thank for sharing his work with the research community.
***
## References
The references associated with each method are provided as the docstring.
If you are going to use the code presented herein for any official study, please refer to: <br /> 
Volkan Ozsarac, Ricardo Monteiro & Gian Michele Calvi (2021). Probabilistic seismic assessment of reinforced concrete bridges using simulated records, Structure and Infrastructure Engineering, DOI: [10.1080/15732479.2021.1956551](https://doi.org/10.1080/15732479.2021.1956551)
***
## Potential Improvements
- Computation of the exact CS
- Addition of 3 component selection
- Addition of spectral matching methods
- Addition of generalized conditional intensity measure approach (GCIM)
- Addition of alternative code-based ground motion selection procedures
