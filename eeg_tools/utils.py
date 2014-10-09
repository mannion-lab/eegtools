"""Various utilities for EEG processing"""

import os
import datetime
import tempfile

import mne

import runcmd


def convert_bdf_to_fiff(bdf_path, fif_path, pos_path=None, overwrite=True):
    """Convert a dataset in BioSemi BDF format into MNE FIF format, adding
    digitiser information and fixing lost information along the way.

    Parameters
    ----------
    bdf_path, fif_path: string
        Paths to the input and output, respectively.
    pos_path: string, optional
        Path to a Polhemus localiser file. This gets converted to a HPTS file.
    overwrite: bool, optional
        Whether its ok to overwrite `fif_path`

    """

    if pos_path is not None:

        # first step is to convert the POS file to HPTS
        (pos_base, pos_ext) = os.path.splitext(pos_path)

        hpts_path = pos_base + ".hpts"

        convert_fastrak_to_hpts(
            pos_path=pos_path,
            hpts_path=hpts_path,
            overwrite=overwrite
        )

    else:

        hpts_path = None

    raw = mne.io.read_raw_edf(
        input_fname=bdf_path,
        hpts=hpts_path,
        verbose="warning"
    )

    chan_mapping = get_unsw_channel_rename_mapping()

    mne.rename_channels(info=raw.info, mapping=chan_mapping)

    raw.save(
        fname=fif_path,
        verbose="warning",
        overwrite=overwrite
    )


def get_unsw_channel_rename_mapping():
    """Get the channel info remapping for the UNSW 64-channel BioSemi EEG
    setup. This can be used in `mne.rename_channels`
    """

    eog_chans = ["EXG" + str(chan) for chan in [1, 2, 5]]

    misc_chans = ["EXG" + str(chan) for chan in [3, 4, 6, 7, 8]]
    misc_chans.extend(["Erg" + str(chan) for chan in [1, 2]])
    misc_chans.extend(["GSR" + str(chan) for chan in [1, 2]])
    misc_chans.extend(["Resp", "Plet", "Temp"])

    # the 'c' at the start is because they won't work with exactly the same
    # channel name
    mapping = {
        eog_chan: ("c" + eog_chan, "eog")
        for eog_chan in eog_chans
    }

    mapping.update(
        {
            misc_chan: ("c" + misc_chan, "misc")
            for misc_chan in misc_chans
        }
    )

    return mapping


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

    """

    if not overwrite and os.path.exists(hpts_path):
        raise ValueError("Output path " + hpts_path + " already exists")

    header = "# Converted from " + pos_path + " to " + hpts_path + "\n"
    header += "# " + str(datetime.datetime.now()) + "\n"

    data = ""

    with open(pos_path, "r") as pos_file:
        raw_data = pos_file.readlines()

    i_eeg = 1
    i_extra = 1

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

                identifier = str(i_extra)

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
