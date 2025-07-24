# Digitising Museum Specimens network tests


## About

As part of the bid preparation for [Digitise UK natural science collections](https://www.ukri.org/opportunity/digitise-uk-natural-science-collections/), the research team needs to test the feasability of uploading the digitised data from the collections store in the Discovery Museum. This repository contains a series of scripts that will test the connection to cloud storage, the ability to upload files of particular types (`.TIFF`, `.csv`, `.json`), the ability and speed of uploading single files of a size similar to an uncompressed image (~120MB), the feasibility and projected speeds of uploading a these files batched, daily (~48GB).

### Project Team

| Name  | Role | Affiliation
| ------------- | ------------- | ------------- |
| Areti Galani  | PI | Newcastle University  |
| Tiago Sousa Garcia | RSE  | Newcastle Universtiy  |

## Built With

Python

### Prerequisites

- [Python 3.12.13](https://www.python.org/downloads/release/python-3123/)
- [pip 24.0](https://pypi.org/project/pip/24.0/)
- `.env` file with `AZURE_STORAGE_CONNECTION_STRING`
- `single_dummy_data_large` folder
- `batch_dummy_data_large` folder

### Installation

#### Create virtual environment
`python3 -m venv /path/to/new/virtual/environment`

#### Activate virtual environment
- On Windows:
`path\to\new\virtual\environment\Scripts\activate`

- On Unix
`source path\to\new\virtual\environment\bin\activate`

#### Install dependencies

`pip install -r requirements.txt`

### Test programme

#### 1. Test connection with Azure storage

This test will attempt to programatically access the pre-configured Azure storage account; it will confirm that it can interact with the account by creating and deleting a storage container in the storage account.

##### Run the test
`python3 -m scripts/01-connection-test.py`

##### Output
Logs will be displayed on the console and saved to `logs/connection_test_*.log`

##### Success
The test will display a success message if it completes successfully. The successful completion of this test confirms that there are no impediments to access the Azure storage account either on the network or on the machine. The digitisation workflow should be able to upload the images automatically.

##### Failure
A failed test means that the digitisation workflow might not be able to include an automated upload step from this machine or network. Upload might still be possible through the browser, or after changes to the network configuration or machine permissions. Recommendation is that the digitisation workflow includes a step where the digital files are physically transported to another location, before upload to cloud storage.



