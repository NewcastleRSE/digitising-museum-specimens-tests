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
`python3 scripts/01-connection-test.py`

##### Output
Logs will be displayed on the console and saved to `logs/connection_test_*.log`

##### Success
The test will display a success message if it completes successfully. The successful completion of this test confirms that there are no impediments to access the Azure storage account either on the network or on the machine. The digitisation workflow should be able to upload the images automatically.

##### Failure
A failed test means that the digitisation workflow might not be able to include an automated upload step from this machine or network. Upload might still be possible through the browser, or after changes to the network configuration or machine permissions. Recommendation is that the digitisation workflow includes a step where the digital files are physically transported to another location, before upload to cloud storage.

#### 2. Test single small file upload

This test will attempt to programatically upload a single small file (~1MB) to the storage account container. It will confirm that there are no impediments to file upload on the machine or the network.

##### Run the test
`python3 ./scripts/02-file-upload.py --folder ./single_dummy_data_small/dummy_file_small.txt --container upload-tests`

##### Output
Logs will be displayed on the console and saved to `logs/file_upload_*.log`

##### Success
The test will display a success message if it completes successfully. The successful completion of this test confirms that there are no impediments to upload small files to the Azure storage account either on the network or on the machine. The digitisation workflow should be able to upload the images automatically.

##### Failure
A failed test means that the digitisation workflow might not be able to include an automated upload step from this machine or network. Upload might still be possible through the browser, or after changes to the network configuration or machine permissions. Recommendation is that the digitisation workflow includes a step where the digital files are physically transported to another location, before upload to cloud storage.

#### 3. Test file extension upload

This test will attempt to programatically upload four small files (~20MB) to the storage account container. It will confirm that there are no impediments to uploading files of the extensions that are likely to be needed: `.csv` or `.json` for structured metadata, and `.tiff` or `.tif` for uncompressed (or losslessly compressed) image files.

##### Run the test
`python3 ./scripts/02-file-upload.py --folder ./single_dummy_data_small --container upload-tests --extensions csv json tiff tif`

##### Output
Logs will be displayed on the console and saved to `logs/file_upload_*.log`

##### Success
The test will display a success message if it completes successfully. The successful completion of this test confirms that there are no impediments to upload files of the type the digitisation workflow is likely to use the Azure storage account either on the network or on the machine. The digitisation workflow should be able to upload the images automatically.

##### Failure
A failed test means that the digitisation workflow might not be able to include an automated upload step from this machine or network. Upload might still be possible through the browser, or after changes to the network configuration or machine permissions. Recommendation is that the digitisation workflow includes a step where the digital files are physically transported to another location, before upload to cloud storage.

#### 4. Test single large file upload

This test will attempt to programatically upload a single large file (~120MB) to the storage account container. It will confirm that there are no impediments to upload single files of a size similar to (or larger than) what we expect an uncompressed TIFF file from a mid- to high-end DSLR to produce.

##### Run the test
`python3 ./scripts/02-file-upload.py --folder ./single_dummy_data_large/dummy_file_001.txt --container upload-tests`

##### Output
Logs will be displayed on the console and saved to `logs/file_upload_*.log`

##### Success
The test will display a success message if it completes successfully. The successful completion of this test confirms that large single files can be uploaded through the network. The time it takes to upload a file will also allow us to investigate whether single file upload or (daily) batch uploads are a better approach.

##### Failure
A failed test means that the digitisation workflow might not be able to include an automated upload step from this machine or network. Upload might still be possible through the browser, or after changes to the network configuration or machine permissions. Recommendation is that the digitisation workflow includes a step where the digital files are physically transported to another location, before upload to cloud storage.

#### 5. Test small files batch upload

This test will attempt to programatically upload a batch of small files (~0.39 GB total) to the storage account container. It will confirm that there are no impediments to the batch upload of files of the number we expect a single digitisation station to produce in a day.

##### Run the test
`python3 ./scripts/02-file-upload.py --folder ./batch_dummy_data_small/ --container upload-tests`

##### Output
Logs will be displayed on the console and saved to `logs/file_upload_*.log`

##### Success
The test will display a success message if it completes successfully. The successful completion of this test confirms that batch upload of c. 400 small files can be uploaded through the network without disturbance. It will establish if batch uploading of daily digitisation is possible in principle.

##### Failure
A failed test means that the digitisation workflow might not be able to include a (daily) batched upload step from this machine or network. If the previous tests have been successful, the recommendation is that the digitisation workflow includes an automated (or user started) upload step per item.

#### 6. Test large files batch upload

This test will attempt to programatically upload a batch of large files (~48 GB total) to the storage account container. It will confirm that there are no impediments to the batch upload of files of the number and the size we expect a single digitisation station to produce in a day. It will ascertain whether a batched (overnight) upload of all the data produced the previous day is a feasible option in defining the digital workflow.

##### Run the test
`python3 ./scripts/02-file-upload.py --folder ./batch_dummy_data_large/ --container upload-tests`

##### Output
Logs will be displayed on the console and saved to `logs/file_upload_*.log`

##### Success
The test will display a success message if it completes successfully. The successful completion of this test confirms that batch upload of c. 400 large files can be uploaded through the network without disturbance and in a usable timeframe. It will establish if batch uploading of daily digitisation is possible for one station.

##### Failure
A failed test means that the digitisation workflow might not be able to include a (daily) batched upload step from this machine or network. If the previous tests have been successful, the recommendation is that the digitisation workflow includes an automated (or user started) upload step per item or a smaller (hourly?) batch upload step.

### Results for `eduroam` in the Catalyst building
- [1. Test connection with Azure storage](#1-test-connection-with-azure-storage) ✅
- [2. Test single small file upload](#2-test-single-small-file-upload) ✅
- [3. Test file extension upload](#3-test-file-extension-upload) ✅
- [4. Test single large file upload](#4-test-single-large-file-upload) ✅
```
2025-07-24 13:32:08,037 - INFO - ✓ Uploaded: dummy_file_001.txt (125,829,120 bytes) -> dummy_file_001.txt in 6.41s (18.73 MB/s)
2025-07-24 13:32:08,038 - INFO - 
==================================================
2025-07-24 13:32:08,038 - INFO - Upload Summary:
2025-07-24 13:32:08,038 - INFO - Total files: 1
2025-07-24 13:32:08,038 - INFO - Successful: 1
2025-07-24 13:32:08,038 - INFO - Failed: 0
2025-07-24 13:32:08,038 - INFO - Total elapsed time: 6.57 seconds (0.11 minutes)
2025-07-24 13:32:08,038 - INFO - Average upload time per file: 6.41 seconds
2025-07-24 13:32:08,038 - INFO - Throughput: 0.15 files/second
2025-07-24 13:32:08,038 - INFO - Container: upload-tests
2025-07-24 13:32:08,038 - INFO - ==================================================
```
- [5. Test small files batch upload](#5-test-small-files-batch-upload) ✅
```
2025-07-24 13:52:53,377 - INFO - Upload Summary:
2025-07-24 13:52:53,377 - INFO - Total files: 400
2025-07-24 13:52:53,377 - INFO - Successful: 400
2025-07-24 13:52:53,377 - INFO - Failed: 0
2025-07-24 13:52:53,377 - INFO - Total elapsed time: 9.77 seconds (0.16 minutes)
2025-07-24 13:52:53,377 - INFO - Average upload time per file: 0.12 seconds
2025-07-24 13:52:53,377 - INFO - Throughput: 40.94 files/second
2025-07-24 13:52:53,377 - INFO - Container: upload-tests
2025-07-24 13:52:53,377 - INFO - ==================================================
```
- [6. Test large files batch upload](#6-test-large-files-batch-upload) ✅
```
==================================================
2025-07-24 14:07:01,321 - INFO - Upload Summary:
2025-07-24 14:07:01,321 - INFO - Total files: 400
2025-07-24 14:07:01,321 - INFO - Successful: 400
2025-07-24 14:07:01,321 - INFO - Failed: 0
2025-07-24 14:07:01,321 - INFO - Total elapsed time: 551.84 seconds (9.20 minutes)
2025-07-24 14:07:01,321 - INFO - Average upload time per file: 6.88 seconds
2025-07-24 14:07:01,321 - INFO - Throughput: 0.72 files/second
2025-07-24 14:07:01,321 - INFO - Container: upload-tests
2025-07-24 14:07:01,321 - INFO - ==================================================
```