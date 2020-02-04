# UMMAP_MRI_Sync_To_Box App

## Using the App

Ensure that you have Python 3.6 or later installed.

To run the app from a Bash command line, you need to know four pieces of information to pass with command flags:

1. `MRI_PATH`: Path to parent directory that holds all MRI directories and files.
2. `JWT_CFG`: Path to the Box JWT config file that authenticates the MADC Server Access App to interact with MADC Box Account files.
3. `BOX_FOLDER_ID`: The Box Folder ID that will hold all the MRI directories and files.
4. `REGEX_SUBFOLDER [REGEX_SUBFOLDER ...]`: Regex patterns for the subdirectories that will be uploaded.

There are two basic modes for this app:

1. The default mode is to simply upload directories and files that don't already exist. 
2. If you pass the `--update_files` flag, the non-default behavior of updating _**all**_ the files to their most recent versions is enabled. This option is very time-consuming as metadata for every source file among those to be uploaded needs to be be compared with its Box destination counterpart. Setting this flag should seldom be used.  

### Command Line Help

To see the command line help from a Bash prompt, run:

```
python3 ummap_mri_sync_to_box.py --help
```

### Canonical Run

Here's an example of a verbose canonical run from a Bash prompt:

```
python3 ummap_mri_sync_to_box.py                             \
  --mri_path MRI_PATH                                        \
  --jwt_cfg JWT_CFG                                          \
  --box_folder_id BOX_FOLDER_ID                              \
  --regex_subfolder REGEX_SUBFOLDER_1 REGEX_SUBFOLDER_2 ...  \
  --verbose
```

### Example Run

Here's an example verbose run from a Bash prompt:

```
python3 ummap_mri_sync_to_box.py                                  \
  --mri_path /path/to/srouce/mri_folder                           \
  --jwt_cfg /path/to/box_jwt_config.json                          \
  --box_folder_id 012345678910                                    \
  --regex_subfolder "^hlp17umm\d{5}_\d{5}$" "^dicom$" "^s\d{5}$"  \
  --verbose
```

### Example Run with Logging

For now, logging should be done with Bash redirect operator `>`:

```
python3 ummap_mri_sync_to_box.py                                  \
  --mri_path /path/to/srouce/mri_folder                           \
  --jwt_cfg /path/to/box_jwt_config.json                          \
  --box_folder_id 012345678910                                    \
  --regex_subfolder "^hlp17umm\d{5}_\d{5}$" "^dicom$" "^s\d{5}$"  \
  --verbose > log/$(date "%Y-%m-%d_%H-%M-%S").log
```

