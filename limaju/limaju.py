#!/usr/bin/env python

"""
A tool to deliberate with majority judgment polling.

Usage:

    ./limaju.py judgments.csv --mentions mentions.txt

where judgments.csv looks like this

    Tyran Sanguinaire, Chien, Écologiste Décroissant
    insuffisant⋅e,excellent⋅e,excellent⋅e
    à rejeter,excellent⋅e,à rejeter
    à rejeter,insuffisant⋅e,très bien

and mentions.txt looks like this

    excellent⋅e
    très bien
    bien
    assez bien
    passable
    insuffisant⋅e
    à rejeter

Run `./limaju.py --help` for more options.
"""

__author__ = "Constituantes"
__version__ = "0.1.0"
__license__ = "MIT"

import sys
import argparse
import csv
import math
import copy
import numpy as np
import matplotlib.pyplot as plt
from pprint import pprint
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


def sort_two_candidates(tally_of, mentions, ca, cb):
    toca = tally_of[ca]
    tocb = tally_of[cb]
    mdca = get_median(toca, mentions)
    mdcb = get_median(tocb, mentions)

    positions = get_positions(mentions)

    if mdca == mdcb:
        cotoca = copy.deepcopy(toca)
        cotocb = copy.deepcopy(tocb)

        while not is_tally_empty(cotoca) and not is_tally_empty(cotocb):
            nemdca = get_median(cotoca, mentions)
            nemdcb = get_median(cotocb, mentions)
            if nemdca == nemdcb:
                decrement_mention(cotoca, nemdca)
                decrement_mention(cotocb, nemdcb)
            else:
                return positions[nemdca] - positions[nemdcb]
        log("EXACT EQUALITY FOUND FOR CANDIDATES")
        log("%s == %s" % (ca, cb))
        return 0
    else:
        return positions[mdca] - positions[mdcb]


def load_judgments_from_string(judgments_string):
    judgments_data_reader = csv.reader(
        StringIO("".join(judgments_string).strip()),
        skipinitialspace=True,
        delimiter=',',
        lineterminator='\n'
    )
    # Load it all up in the memory, who cares?
    judgments_data = []
    for judgments in judgments_data_reader:
        if not judgments:
            #log("Skipping empty line at row %d..." % current_row)
            continue
        judgments_data.append(judgments)

    return judgments_data


def load_mentions_from_string(ms, sep="\n"):
    return [m.strip() for m in ms.strip().split(sep) if m and m.strip()]


def deliberate(judgments_data,
               mentions,
               skip_cols=0):

    ignore_blanks = False
    candidates_list = list()
    everyones_judgments = dict()
    skip_rows = 0
    header_on_row = skip_rows + 0  # toggle 0 to -1 to disable header

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
                ["Candidate %s"%(chr(64+i)) for i in range(len(judgments))]

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
            judgments_tallies,
            mentions,
            ca, cb)

    sorted_candidates = sort_candidates(
        judgments_tallies,
        candidates_list,
        mentions)

    return sorted_candidates, judgments_tallies


def sort_candidates(judgments_tallies, candidates, mentions):
    """
    :param judgments_tallies: Dict, candidate => mention => int
    :param candidates: List
    :param mentions: List, highest to lowest
    :return:
    """
    def _cmp_candidates(ca, cb):
        # Here we could hook to external, replaceable classes
        # to simplify usage of other algorithms.
        return sort_two_candidates(
            judgments_tallies,
            mentions,
            ca, cb
        )

    return sorted(
        candidates,
        key=cmp_to_key(_cmp_candidates)
    )


def plot_merit_profile(judgments_tallies, candidates, mentions, filename=None):
    """
    :param filename: String, should match `*.png` or `*.pdf`. Paths are allowed.
    """

    pprint(judgments_tallies)
    pprint("candidates")
    pprint(candidates)
    pprint("mentions")
    pprint(mentions)

    bar_girth = 0.62
    candidates = [c for c in reversed(candidates)]  # :(|) oOoK

    # opinions = [  # for each mention, how many for each candidate
    #     (20, 35, 30, 35, 27, 30, 35, 27), # excellent
    #     (25, 32, 34, 20, 25, 30, 35, 27), # etc.
    #     (25, 32, 34, 20, 25, 30, 35, 27),
    #     (25, 32, 34, 20, 25, 30, 35, 27),
    #     (25, 32, 34, 20, 25, 30, 35, 27),
    #     (20, 35, 30, 35, 27, 30, 35, 27),
    #     (20, 35, 30, 35, 27, 30, 35, 27),
    # ]

    opinions = [[judgments_tallies[c][m] for c in candidates] for m in mentions]

    # candidates = ('G1', 'G2', 'G3', 'G4', 'G5')
    # mentions = (
    #     u"excellent⋅e",
    #     u"très bien",
    #     u"bien",
    #     u"assez bien",
    #     u"passable",
    #     u"insuffisant⋅e",
    #     u"à rejeter",
    # )

    colors = (
        (0, 0.49, 0.24, 1),
        (0.01, 0.67, 0.35, 1),
        (0.49, 0.76, 0.22, 1),
        (0.78, 0.84, 0, 1),
        (0.99, 0.7, 0, 1),
        (0.93, 0.43, 0, 1),
        (0.88, 0.21, 0.11, 1),
    )

    # candidates = (
    #     "Tyran Sanguinaire",
    #     "Chien",
    #     "Écologiste Décroissant",
    #     "Capitaliste Prédateur",
    #     "Imposteur Crapuleux",
    #     "Nationaliste Identitaire",
    #     "Camarade Communiste",
    #     "Marianne",
    # )

    candidates_amount = len(candidates)

    # vlorp = 0.05
    barhs = []
    legends = []
    ind = [i for i in range(candidates_amount)]
    leftOffset = (0,) * candidates_amount
    judgments_sum = (0,) * candidates_amount

    for opinion, mention in zip(opinions, mentions):
        judgments_sum = tuple(p + q for p, q in zip(opinion, judgments_sum))
    judgments_count = max(judgments_sum)

    vlorp = judgments_count * 0.003

    for i, mention in enumerate(mentions):
        #print(u"Plotting bars of mention %s…" % mention)
        opinion = opinions[i]
        barh = plt.barh(ind, opinion, bar_girth, left=leftOffset, color=colors[i])
        barhs.append(barh)
        legends.append(barh[0])
        # At some point, we should either go full numpy or not at all
        # The vlorp is a nasty hack to show white separators between colors
        leftOffset = tuple(p + q + vlorp for p, q in zip(opinion, leftOffset))

    # p1 = plt.barh(ind, menMeans, bar_girth)
    # p2 = plt.barh(ind, womenMeans, bar_girth, left=menMeans)

    adjusted_width = max(leftOffset)

    plt.title('Merit Profiles')
    plt.ylabel('Candidates')
    plt.yticks(ind, candidates)
    plt.xlabel('Mentions given')
    plt.xticks([adjusted_width - vlorp], [judgments_count])
    # plt.xticks(np.arange(0, 81, 10))

    plt.legend(
            legends, mentions,
            ncol=len(mentions),
            loc='upper center',
            prop={'size': 6},
            fancybox=True,
            shadow=True,
            bbox_to_anchor=(0.5, -0.15),
    )

    plt.axvline(x=adjusted_width*0.5, linestyle='--')

    # ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05, fancybox=True, shadow=True, ncol=5)
    # ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05, fancybox=True, shadow=True, ncol=5)

    mng = plt.get_current_fig_manager()
    mng.full_screen_toggle()

    if filename is not None:
        # plt.savefig(filename)
        plt.savefig(filename, dpi=200, bbox_inches='tight')
    else:
        plt.show()
    plt.clf()


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

    log("\nRead judgments from %d judges." % (len(judgments_data)-1))

    deliberation, tally = deliberate(
        judgments_data, mentions,
        int(args.skip_cols)
    )

    log("\nDELIBERATION")
    for i, candidate in enumerate(deliberation):
        log("%02d.\t%18s\t%s" % (
            i+1,
            get_median(tally[candidate], mentions),
            candidate,
        ))


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
