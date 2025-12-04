import datetime
import argparse
import dateutil.parser

def add_now(arg_parser: argparse.ArgumentParser) -> None:
    arg_parser.add_argument(
        '-n',
        '--now',
        dest='now',
        type=dateutil.parser.parse,
        default=datetime.datetime.now(),
        help="The time for the operation, if not the system clock time.",
    )

def add_card_file_encoding(arg_parser: argparse.ArgumentParser) -> None:
    arg_parser.add_argument(
        '-e',
        '--encoding',
        dest='card_file_encoding',
        type=str,
        default='utf-8',
        help="The encoding to use for card files.",
    )
