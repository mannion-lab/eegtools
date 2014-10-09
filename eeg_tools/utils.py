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

        hpts_path = os.path.join(pos_base, ".hpts")

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



def get_unsw_channel_rename_mapping():




def fix_channel_types(fif_path, alias_path=None):
    """Assign channels in a FIF file to the correct type, which is lost when
    converting from BDF format.

    Parameters
    ----------
    fif_path: string
        Path to the FIF file to alter.
    alias_path: string, optional
        Path to the channel change information file. If not given, a standard
        based on the 64-channel fix at UNSW is applied.

    """

    if alias_path is None:

        eog_chans = ["EXG" + str(chan) for chan in [1, 2, 5]]
        misc_chans = ["EXG" + str(chan) for chan in [3, 4, 6, 7, 8]]

        misc_chans.extend(["Erg" + str(chan) for chan in [1, 2]])
        misc_chans.extend(["GSR" + str(chan) for chan in [1, 2]])
        misc_chans.extend(["Resp", "Plet", "Temp"])

        eog_code = 202
        misc_code = 502

        chan_out = [
            ":".join([chan_name] * 2 + [str(eog_code)])
            for chan_name in eog_chans
        ]

        chan_out.extend(
            [
                ":".join([chan_name] * 2 + [str(misc_code)])
                for chan_name in misc_chans
            ]
        )

        alias_path = tempfile.NamedTemporaryFile(delete=False)

        alias_path.file.write("\n".join(chan_out))

        alias_path.close()

        alias_path = alias_path.name

    cmd = [
        "mne_rename_channels",
        "--fif", fif_path,
        "--alias", alias_path
    ]

    runcmd.run_cmd(" ".join(cmd))



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

    if overwrite and os.path.exists(hpts_path):
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
