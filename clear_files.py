import os
import shutil

def clear_directory(directory_path):
    # Check if the directory exists
    if os.path.exists(directory_path) and os.path.isdir(directory_path):
        # Iterate over all the files in the directory
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            try:
                # Check if it is a file or a directory and delete accordingly
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Remove file or link
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Remove directory
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
    else:
        print(f'{directory_path} is not a valid directory, please fix this before proceeding')

def clear_all(image_directory):
    clear_directory(image_directory)
    # exist_ok so a leftover 'frames'/'tabs' (e.g. one clear_directory could not
    # remove) never crashes with "file already exists".
    os.makedirs(os.path.join(image_directory, "frames"), exist_ok=True)
    os.makedirs(os.path.join(image_directory, "tabs"), exist_ok=True)

