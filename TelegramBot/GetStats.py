# Script to retrieve stats about the number of hits

import pickle, pprint

if __name__ == '__main__':

    with open('stats.pickle', 'rb') as f:
        saved_dict = pickle.load(f)

    pprint.pprint(saved_dict)