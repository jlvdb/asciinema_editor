import asciinema_editor as ascii


if __name__ == "__main__":
    # Postprocess a terminal recording:
    # - Cut at the beginning and end
    # - Show a custom command prompt
    # - Generate a command that is typed into the terminal
    # - Show the part of the original recording (cast) that shows the output of the command
    # - Show the custom prompt again

    # load and clip the recorded cast
    full_cast = ascii.Recording.from_file("yaw_cli_raw.cast")
    _, cast = full_cast.split_before(33)
    cast, _ = cast.split_before(-3)
    cast.trim()  # remove offset from clipped records
    cast = cast.replace("/Users/janluca/dev/CCs/testing", "/Users/jlvdb")

    prompt = ascii.generate_prompt("jlvdb", "yaw")  # shows: 'jlvdb@yaw ~ $ '

    # create the new cast
    movie = ascii.Recording.empty_from(cast)
    # start with the prompt and wait 6 seconds
    movie += prompt
    movie += ascii.wait(6)
    # type in the command and wait 2 seconds, then "press enter"
    movie += ascii.type_text("yaw_cli run -vv test_run -s test_setup.yaml --progress")
    movie += ascii.wait(2)
    movie += ascii.type_text("\n\r")  # press enter
    # replay the command output from the cast
    movie += cast
    # show the prompt again and wait 10 seconds before ending the cast
    movie += prompt
    movie += ascii.end(10)

    # write the new cast and replay it afterwards at 3x speed
    movie.write("yaw_cli.cast")
    movie.replay(3)
