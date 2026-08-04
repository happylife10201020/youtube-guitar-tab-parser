import argparse
import os
from clear_files import clear_all
from download_frames import download
from extract_tab_pics import extract_tab
from clean_tab import make_pdf

def main():
    parser = argparse.ArgumentParser(description='YouTube Guitar Tab Parser')
    parser.add_argument('url', help='The YouTube URL to parse.')
    parser.add_argument('output_dir', nargs='?', default='output', help='The directory to save the output files.')
    parser.add_argument('--overlap', type=float, default=None,
                        help='Fraction (0-1) of each line the video repeats from the previous line, '
                             'trimmed from the PDF. Omit to auto-detect, use 0 to disable trimming.')
    args = parser.parse_args()

    main_directory = args.output_dir
    youtube_url = args.url

    if not os.path.exists(main_directory):
        os.makedirs(main_directory)

    clear_all(main_directory)
    download(main_directory, youtube_url)
    extract_tab(main_directory)
    make_pdf(main_directory, overlap_fraction=args.overlap)

if __name__ == '__main__':
    main()
