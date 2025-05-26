# TMSi MATLAB LSL Interface #
Python apps/tools for interacting with MATLAB TMSi streams via LSL. 

## Installation ##
1. Clone this repository.
```bat
git clone git@github.com:Neuro-Mechatronics-Interfaces/TMSi_MATLAB_LSL.git && cd TMSi_MATLAB_LSL
```
2. Create your local Python environment. Call `python` (system Python interpreter) with the `module` option (`-m`) specifying `venv`, which should be a default package with standard Python installations. If `venv` is missing, you may need a more recent Python interpreter version:
```bat
python -m venv .venv && call .venv\Scripts\activate
```
Your terminal should now say `(.venv)` in front of the file path (thanks to `call .venv\Scripts\activate` - now, in this terminal, when you lead with `python` it will refer to the executable installed in `.venv\Scripts\python.exe` instead of your usual Python interpreter).  
3. Add Python requirements to your local Python environment. 
```bat
python -m pip install -r requirements.txt
```
If you type `pip list` you should see that the installed packages are similar or identical to the contents of `requirements.txt`. 

## Usage ##
After following the steps in [Installation](#installation), you can start logging parameters and trial metadata using:  
```bat
python run_lsl_logger.py
```

