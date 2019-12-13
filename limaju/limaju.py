#!/usr/bin/env python

"""
A tool to summarize majority judgment polling.
"""

__author__ = "Constituantes"
__version__ = "0.1.0"
__license__ = "MIT"

import sys
import argparse
import csv
import math
import copy
from io import StringIO
from functools import cmp_to_key

PY2 = sys.version_info.major == 2

VERBOSITY_NONE = 0
VERBOSITY_SOME = 1
VERBOSITY_MUCH = 2
VERBOSITY_VERY = 3


def log(message):
    print(message)


def find_file(some_vague_path):
    return some_vague_path


def is_string(that_thing):
    return \
        isinstance(that_thing, basestring if PY2 else str) \
        or \
        isinstance(that_thing, unicode if PY2 else str) \
        or \
        isinstance(that_thing, basestring if PY2 else (str, bytes)) \
        or \
        isinstance(that_thing, bytes)


def get_positions(mentions):
    mentions_dict = dict()
    for i, mention in enumerate(mentions):
        mentions_dict[mention] = i
    return mentions_dict


def get_median(tally, mentions):
    low = True
    count = 0
    for mention in tally:
        count += tally[mention]

    # Lowest mention is the default
    median = mentions[-1]

    if 0 == count:
        return median

    median_index = math.floor((count + (-1 if low else 1)) / 2.0)

    current = 0
    for mention in reversed(mentions):  # lowest to highest
        mention_min = current
        current += tally[mention]
        mention_max = current

        if mention_min <= median_index < mention_max:
            median = mention
            break

    return median


def is_tally_empty(tally):
    for mention in tally:
        if 0 < tally[mention]:
            return False
    return True


def decrement_mention(tally, mention):
    assert tally[mention] > 0
    tally[mention] -= 1


def sort_two_candidates(judgments_of, tally_of, mentions, ca, cb):
    toca = tally_of[ca]
    tocb = tally_of[cb]
    mdca = get_median(toca, mentions)
    mdcb = get_median(tocb, mentions)

    positions = get_positions(mentions)

    if mdca == mdcb:
        cotoca = copy.copy(toca)
        cotocb = copy.copy(tocb)

        while not is_tally_empty(cotoca) and not is_tally_empty(cotocb):
            nemdca = get_median(cotoca, mentions)
            nemdcb = get_median(cotocb, mentions)
            if nemdca == nemdcb:
                decrement_mention(cotoca, nemdca)
                decrement_mention(cotocb, nemdcb)
            else:
                return positions[nemdca] - positions[nemdcb]

        return 0
    else:
        return positions[mdca] - positions[mdcb]


def main(args_parser, args):  # move to bottom, no need for a func
    log("MAJORITY JUDGMENT POLLING -- Version %s" % __version__)

    # In decreasing order.
    default_mentions = [
        'EXCELLENT',
        'VERY GOOD',
        'GOOD',
        'SOMEWHAT GOOD',
        'PASSABLE',
        'POOR',
        'REJECT',
    ]
    if not args.mentions_file:
        mentions = default_mentions
    else:
        with open(args.mentions_file) as f:
            mentions = [l.strip() for l in f.readlines() if l and l.strip()]

    log("\nGoing to use the following mentions:")
    log(''+(', '.join(mentions)))

    if args.input_file is None:
        exit(1)

    log("\nWaiting for input judgments...")
    log("(use CTRL+D to exit)")
    input_csv_strings = args.input_file.readlines()

    if not input_csv_strings:
        log("Please provide an input CSV file.")
        args_parser.print_help()
        args_parser.exit(1)

    judgments_data = load_judgments_from_string(input_csv_strings)
    # judgments_data = csv.reader(
    #     StringIO("".join(input_csv_strings).strip()),
    #     skipinitialspace=True,
    #     delimiter=',',
    #     lineterminator='\r\n'
    # )

    deliberation, tally = deliberate(
        judgments_data, mentions,
        int(args.skip_cols)
    )

    for i, candidate in enumerate(deliberation):
        log("%02d.\t%18s\t%s" % (
            i+1,
            get_median(tally[candidate], mentions),
            candidate,
        ))


def load_judgments_from_string(judgments_string):
    judgments_data = csv.reader(
        StringIO("".join(judgments_string).strip()),
        skipinitialspace=True,
        delimiter=',',
        lineterminator='\n'
    )

    return judgments_data


def load_mentions_from_string(ms):
    return [m.strip() for m in ms.strip().split() if m and m.strip()]


def deliberate(judgments_data,
               mentions,
               skip_cols=0):

    ignore_blanks = False
    candidates_list = list()
    everyones_judgments = dict()
    skip_rows = 0
    header_on_row = skip_rows + 0  # Set to -1 to disable header

    if is_string(judgments_data):
        judgments_data = load_judgments_from_string(judgments_data)

    if is_string(mentions):
        mentions = load_mentions_from_string(mentions)

    current_row = -1
    for judgments in judgments_data:
        current_row += 1

        judgments = judgments[skip_cols:]

        if current_row < skip_rows:
            continue

        if current_row == header_on_row:
            candidates_list = judgments
            continue

        if not judgments:
            log("Skipping empty line at row %d..." % current_row)
            continue

        if not candidates_list:
            candidates_list = \
                ["Candidate %s"%(chr(i)) for i in range(len(judgments))]

        for i, mention in enumerate(judgments):
            if mention is None or mention == '':
                if ignore_blanks:
                    continue
                else:
                    judgments[i] = mentions[-1]
                    continue
            if mention not in mentions:
                log("Found unknown mention `%s' at row %d." % (
                    mention, current_row
                ))
                log("Use --mentions to specify a mentions file.")
                exit(1)

        for i in range(len(candidates_list)):
            candidate = candidates_list[i]
            if candidate not in everyones_judgments:
                everyones_judgments[candidate] = list()
            everyones_judgments[candidate].append(judgments[i])

    mentions_dict = get_positions(mentions)

    # Sort the mentions of each candidate.
    for candidate in everyones_judgments:
        s = sorted(
            everyones_judgments[candidate],
            key=lambda m: mentions_dict[m])
        everyones_judgments[candidate] = s

    judgments_tallies = dict()
    for i in range(len(candidates_list)):
        candidate = candidates_list[i]
        if candidate not in judgments_tallies:
            judgments_tallies[candidate] = dict()
        for mention in mentions:
            if mention not in judgments_tallies[candidate]:
                judgments_tallies[candidate][mention] = 0
        for mention in everyones_judgments[candidate]:
            if mention not in judgments_tallies[candidate]:
                # mention unknown
                log("Warning: Unknown mention: %s" % mention)
                judgments_tallies[candidate][mention] = 0
            judgments_tallies[candidate][mention] += 1

    # log("Candidates")
    # log(candidates_list)
    # log(judgments_tallies)

    def _cmp_candidates(ca, cb):
        # Here we could hook to external, replaceable classes
        # to simplify usage of other algorithms.
        return sort_two_candidates(
            everyones_judgments,
            judgments_tallies,
            mentions,
            ca, cb
        )

    sorted_candidates = sorted(
        candidates_list,
        key=cmp_to_key(_cmp_candidates)
    )

    return sorted_candidates, judgments_tallies


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # Optional argument flag which defaults to False
    # parser.add_argument(
    #     '-f',
    #     '--flag',
    #     action="store_true",
    #     default=False,
    #     help=""
    # )

    parser.add_argument(
        'input_file',
        nargs='?',
        type=argparse.FileType('r'),
        help="A CSV file with the judgments.",
        default=sys.stdin
    )

    parser.add_argument(
        "-m",
        "--mentions",
        action="store",
        dest="mentions_file",
        help="""
        A text file with one mention per line,
        in order from highest to lowest.
        """
    )

    parser.add_argument(
        "--skip-cols",
        action="store",
        default=0,
        dest="skip_cols",
        help="Amount of columns to skip on the left."
    )

    # Optional verbosity counter (eg. -v, -vv, -vvv, etc.)
    parser.add_argument(
        '-v',
        '--verbose',
        action='count',
        default=0,
        help="Verbosity (-v, -vv, etc)"
    )

    # Specify output of '--version'
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s (version {version})'.format(version=__version__)
    )

    args = parser.parse_args()
    main(parser, args)
