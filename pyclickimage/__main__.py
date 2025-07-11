import argparse
import cv2
from .run import run

def __main__() -> None:
    r"""
    Main entry point of the package.

    This method contains the script to run if the user enter the name of the package on the command line. 

    .. code-block:: console
        pyclickimage
        
    """
    raise NotImplementedError("This is a placeholder for the main entry point of the package. Use 'pyclickimage-gui' to run the GUI application.")



def __main_gui__() -> None:
    r"""
    Graphical user interface entry point of the package.

    This method contains the script to run if the user enter the name of the package on the command line with the ``gui`` extension.

    .. code-block:: console
        pyclickimage-gui

    This will launch the GUI application for image clicking and saving coordinates.

    You can also specify an image file to be displayed ``--image`` or ``-i`` and a CSV file path to save the click coordinates ``--output`` or ``-o``.
        
    """
    # Parser for command line arguments
    parser = argparse.ArgumentParser(description="PyClickImage GUI application.")
    parser.add_argument(
        "-i", "--image", type=str, help="Path to the image file to be displayed."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Path to save the CSV file with click coordinates.",
    )
    args = parser.parse_args()

    if args.image is not None:
        image = cv2.imread(args.image)
    else:
        image = None

    # Launch the GUI application
    run(image=image, output=args.output)

