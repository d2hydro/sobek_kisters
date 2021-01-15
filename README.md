# sobek_kisters
Sobek adapter to kisters network store. Including a generic Sobek reader and a writer to the kisters network store and timeseries

## Installation

### Create a SOBEK environment
Use the environment.yml in the repository to create the proper python environment for SOBEK in command prompt

```
conda env create -f environment.yml
```

After creating the environment, activate it by running this in the command prompt:

```
conda activate sobek
```

In the activated environment you install this module by:

```
pip install .
```

If you wish to upload timeseries to the Kisters TSA Store, request that library and install it the same way. Kisters will supply an url to the TSA Store.

## Run examples/de_tol

### config
For uploading a model to the Kisters network store you'll need a Kisters client-id and password. Add the file examples/de_tol/config.py (see examples/de_tol/config_template.py) where you define the following parameters:

```
LIT_DIR = Path()  # Path to the Sobek project
DATA_DIR = Path() # Path to the data-dir where you store your groups.json (see examples/de_tol/data as example)
CLIENT_ID = 	  # Kisters client-id
CLIENT_SECRET =   # Kisters password
CASE_NAME =       # Sobek case-name
KISTERS_NAME =    # Name to be used in Kisters network store
TSA_STORE         # url to the Kisters TSA Store
```

### groups
In data/groups.json you can define groups, used in Kisters for visualisation purposes.

```
{
	"type": "PumpingStation",        #Kisters group-type
	"uid": "G2901",                  #uid used in Kisters network store
	"display_name": "gemaal De Tol", #display name used by Kisters network store
	"us_node": "PG0402_",            #Upstream Sobek-node of the group
	"ds_node": "bndPG0402",          #Downstream Sobek-node of the group
	"schematic_location": {          #Location of the group in Kisters network store as shown
		"x": 553613.57920871,
		"y": 6830004.305543325,
		"z": 0.0
	},
	"location": {                    #Location of the group in Kisters network store
		"x": 553613.57920871,
		"y": 6830004.305543325,
		"z": 0.0
	}
```

In the example above, all sobek reaches and nodes between Sobek-node PG0402 and bndPG0402 (both included) will be in included in a group of the type PumpingStation with Kisters uid G2901 and name gemaal de Tol. It will be displayed in location x,y = 553613.57920871,6830004.305543325 (both in web-mecator projection).

### upload your model
In an activated environment you can now upload your topology by:

```
python upload_topology.py
```

### upload time series
In an activated environment you can upload time series by:

```
python upload_time_series.py
```

This assuming you have the TSA store installed and an url optained.