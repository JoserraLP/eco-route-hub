# Eco-Traffic APP: Speed profile simulator
The Eco-Traffic App speed profile simulator consists on a series of functionalities and models that allows to simulate 
the behavior of a driver type using a given vehicle (and its features) on a route considering different metrics such 
as slope, distance, speed limits, etc.

## File structure
This component is developed as a Python library with the following architecture:
- **path**: storing everything related to the routes and its segments.
- **static**: constants default values.
- **utils**: several util functions.
- **vehicle**: consisting on all the classes related to the vehicle model, its movement on a given route, and 
- power/energy estimators.


## Additional files
Besides, there is another folder on the project ("matlab_simulators") which stores the different versions of the 
simulator implemented in MATLAB.


## Installation
This library is required to be installed in order to be used, alongside with other libraries (stored in 
"requirements.txt" file). 

~~~
pip install -r requirements.txt
~~~

## Execution command

We can execute the following command, on the "speed_profile_simulator" folder:
~~~
python simulator.py
~~~
