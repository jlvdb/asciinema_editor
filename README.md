# asciinema_editor

Edit terminal output recordings captured with ASCIINEMA.

## asciinema

Install ``asciinema`` to record and replay the casts of terminal output: https://github.com/asciinema/asciinema


## Installation

Install this code from its repository using pip

    git clone git@github.com:jlvdb/asciinema_editor
    cd asciinema_editor
    pip install .

## Usage

There is an example in the ``examples/`` directory which covers most of the functionality of the package:

    cd examples
    python create_yaw_cast.py

One way to convert the recording to a gif is using the online tool [``gifcast``](https://dstein64.github.io/gifcast/). Upload the ``.cast`` file, configure the conversion and download the gif.
