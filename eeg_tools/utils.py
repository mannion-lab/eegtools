"""Various utilities for EEG processing"""

import os
import datetime


def convert_fastrak_to_hpts(pos_path, hpts_path, overwrite=False):
    """Convert a set of electrode locations recorded with a Polhemus FASTRAK
    (and saved in '.pos' format) to the 'hpts' format that can be used with the
    MNE suite.

    Parameters
    ----------
    pos_path: string
        Path to the Polhemus 'pos' file, as written by BrainStorm.
    hpts_path: string
        Path to the 'hpts' file to write.
    overwrite: bool, optional
        Whether to overwrite ``hpts_path``, if it exists.

    Notes
    -----
    * The first electrode that is digitised is assigned as the reference
      electrode (label of 0)

    """

    if overwrite and os.path.exists(hpts_path):
        raise ValueError("Output path " + hpts_path + " already exists")

    header = "# Converted from " + pos_path + " to " + hpts_path + "\n"
    header += "# " + str(datetime.datetime.now()) + "\n"

    data = ""

    with open(pos_path, "r") as pos_file:
        raw_data = pos_file.readlines()

    i_eeg = 0
    i_extra = 0

    # ignore the first
    for pos_data in raw_data[1:]:

        pos_info = pos_data.strip().split("\t")

        if len(pos_info) == 4:

            category = "cardinal"

            pos_id = pos_info[0]

            if pos_id == "NA":
                identifier = "2"
            elif pos_id == "LPA":
                identifier = "1"
            elif pos_id == "RPA":
                identifier = "3"

            (pos_x, pos_y, pos_z) = pos_info[1:]

        elif len(pos_info) == 5:

            (pos_id, pos_name, pos_x, pos_y, pos_z) = pos_info

            # if the name is empty, must be shape points
            if pos_name == "":

                category = "extra"

                identifier = str(i_extra + 1)

                i_extra += 1

            # otherwise, must be EEG
            else:

                category = "eeg"

                identifier = str(i_eeg)

                i_eeg += 1

        # position is given in cm, so needs to be converted to mm
        [pos_x, pos_y, pos_z] = [
            str(float(pos) * 10)
            for pos in [pos_x, pos_y, pos_z]
        ]

        data += " ".join([category, identifier, pos_x, pos_y, pos_z]) + "\n"

    with open(hpts_path, "w") as hpts_file:
        hpts_file.write(header + data)
